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


def master_acx(src: Path, dst: Path, head_s: float, tail_s: float, target_rms_db: float = -20.0) -> dict:
    """Master one chapter WAV to ACX specs and return the measured values.

    Steps: 44.1 kHz mono, gentle 70 Hz high-pass, a downward expander that pushes
    breaths-between-words hiss under -60 dB, gain to the RMS target, then a true-peak
    limiter at -3.5 dBFS so peaks stay under -3 dB. Room tone is digital near-silence
    padded at both ends.
    """
    tmp = dst.with_suffix(".stage1.wav")
    ffmpeg(
        "-i", str(src),
        "-af",
        "aresample=44100:resampler=soxr,aformat=channel_layouts=mono,"
        "highpass=f=70,"
        "agate=threshold=0.003:ratio=3:range=0.0316:attack=5:release=150",
        "-ar", "44100", "-ac", "1", "-c:a", "pcm_f32le", str(tmp),
    )
    current = acx_measure(tmp)["rms_db"]
    gain = target_rms_db - current
    ffmpeg(
        "-i", str(tmp),
        "-af",
        f"volume={gain:.2f}dB,"
        "alimiter=limit=0.668:attack=5:release=50:level=disabled,"
        f"adelay={int(head_s * 1000)}:all=1,apad=pad_dur={tail_s}",
        "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(dst),
    )
    tmp.unlink(missing_ok=True)
    measured = acx_measure(dst)
    # A second, small trim if limiting pulled the RMS below the window.
    if not -23.0 <= measured["rms_db"] <= -18.0:
        fix = dst.with_suffix(".fix.wav")
        ffmpeg(
            "-i", str(dst),
            "-af", f"volume={target_rms_db - measured['rms_db']:.2f}dB,alimiter=limit=0.668:level=disabled",
            "-c:a", "pcm_s16le", str(fix),
        )
        fix.replace(dst)
        measured = acx_measure(dst)
    return measured


def silence(seconds: float, sr: int) -> np.ndarray:
    return np.zeros(int(round(seconds * sr)), dtype=np.float32)


def parse_db(text: str, key: str) -> float | None:
    m = re.search(rf"{key}:\s*(-?[\d.]+|-inf)", text)
    if not m or m.group(1) == "-inf":
        return None
    return float(m.group(1))
