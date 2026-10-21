"""ffmpeg helpers: measuring levels, normalizing, and ACX mastering."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"


def run(args: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(args)}\n{proc.stderr[-2000:]}")
    return proc


def ffmpeg(*args: str) -> subprocess.CompletedProcess:
    return run([FFMPEG, "-hide_banner", "-nostdin", "-y", *args])


def duration(path: Path | str) -> float:
    out = run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    return float(out.stdout.strip())


def loudnorm_measure(path: Path | str, target_i: float, target_tp: float) -> dict:
    proc = ffmpeg(
        "-i", str(path),
        "-af", f"loudnorm=I={target_i}:TP={target_tp}:LRA=11:print_format=json",
        "-f", "null", "-",
    )
    blob = proc.stderr[proc.stderr.rfind("{"): proc.stderr.rfind("}") + 1]
    return json.loads(blob)


def acx_measure(path: Path | str, window: float = 0.05) -> dict:
    """Measure the three ACX numbers on a file.

    rms_db: overall RMS level in dBFS (ACX: -23 to -18).
    peak_db: highest sample peak in dBFS (ACX: -3 or lower).
    noise_floor_db: RMS of the quietest 0.5 s window, the way ACX Check measures
    room tone (ACX: -60 or lower).
    """
    audio, sr = sf.read(str(path), dtype="float64", always_2d=True)
    mono = audio.mean(axis=1)
    rms = np.sqrt(np.mean(mono**2)) if mono.size else 0.0
    peak = np.max(np.abs(mono)) if mono.size else 0.0

    win = int(sr * 0.5)
    hop = int(sr * window)
    floor = 0.0
    if mono.size >= win:
        sq = np.concatenate([[0.0], np.cumsum(mono**2)])
        starts = np.arange(0, mono.size - win + 1, hop)
        rms_windows = np.sqrt((sq[starts + win] - sq[starts]) / win)
        floor = float(rms_windows.min())

    def db(x: float) -> float:
        return round(float(20 * np.log10(max(x, 1e-10))), 1)

    return {
        "rms_db": db(rms),
        "peak_db": db(peak),
        "noise_floor_db": db(floor),
        "sample_rate": sr,
        "channels": audio.shape[1],
        "seconds": round(mono.size / sr, 2),
    }


def acx_pass(m: dict) -> bool:
    return -23.0 <= m["rms_db"] <= -18.0 and m["peak_db"] <= -3.0 and m["noise_floor_db"] <= -60.0


ROOM_TONE_DB = -70.0  # ACX wants the noise floor at or below -60 dB
LIMIT_DBFS = -3.5  # ACX wants peaks at or below -3 dB


def room_tone(n: int, sr: int, level_db: float = ROOM_TONE_DB, seed: int = 7) -> np.ndarray:
    """Faint, steady pink noise. ACX reviewers reject pure digital silence as unnatural."""
    rng = np.random.default_rng(seed)
    white = rng.standard_normal(n + sr)
    spectrum = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(white.size, 1 / sr)
    spectrum[1:] /= np.sqrt(freqs[1:])
    spectrum[0] = 0
    pink = np.fft.irfft(spectrum, white.size)[:n]
    pink /= np.sqrt(np.mean(pink**2)) + 1e-12
    return (pink * 10 ** (level_db / 20)).astype(np.float64)


def master_acx(src: Path, dst: Path, head_s: float, tail_s: float, target_rms_db: float = -20.0) -> dict:
    """Master one chapter WAV to ACX specs and return the measured values.

    Steps: 44.1 kHz mono with a gentle 70 Hz high-pass, gain so the overall RMS lands
    on target_rms_db, a look-ahead limiter at -3.5 dBFS, then head/tail padding and
    a -70 dB pink-noise room tone under everything. Output is 16-bit 44.1 kHz mono.
    """
    sr = 44100
    tmp = dst.with_suffix(".stage1.wav")
    ffmpeg(
        "-i", str(src),
        "-af", "aresample=44100:filter_size=64:cutoff=0.98,highpass=f=70",
        "-ar", str(sr), "-ac", "1", "-c:a", "pcm_f32le", str(tmp),
    )
    gain = 0.0
    for _ in range(3):  # limiting lowers RMS a little; re-aim until it lands in the window
        gain += target_rms_db - acx_measure(tmp if gain == 0 else dst.with_suffix(".stage2.wav"))["rms_db"]
        stage2 = dst.with_suffix(".stage2.wav")
        ffmpeg(
            "-i", str(tmp),
            "-af", f"volume={gain:.2f}dB,alimiter=limit={10 ** (LIMIT_DBFS / 20):.4f}:attack=5:release=50:level=disabled",
            "-c:a", "pcm_f32le", str(stage2),
        )
        if abs(acx_measure(stage2)["rms_db"] - target_rms_db) <= 0.5:
            break
    speech, _ = sf.read(str(stage2), dtype="float64")
    tmp.unlink(missing_ok=True)
    stage2.unlink(missing_ok=True)

    out = np.concatenate([np.zeros(int(head_s * sr)), speech, np.zeros(int(tail_s * sr))])
    out = out + room_tone(out.size, sr)
    out = np.clip(out, -(10 ** (LIMIT_DBFS / 20)), 10 ** (LIMIT_DBFS / 20))
    sf.write(str(dst), out, sr, subtype="PCM_16")
    return acx_measure(dst)


def silence(seconds: float, sr: int) -> np.ndarray:
    return np.zeros(int(round(seconds * sr)), dtype=np.float32)


def parse_db(text: str, key: str) -> float | None:
    m = re.search(rf"{key}:\s*(-?[\d.]+|-inf)", text)
    if not m or m.group(1) == "-inf":
        return None
    return float(m.group(1))
