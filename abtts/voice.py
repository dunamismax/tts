"""Prepare a reference voice clip for cloning."""

from __future__ import annotations

from pathlib import Path

import yaml

from .audio import duration, ffmpeg, loudnorm_measure

TRIM = (
    "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.15,"
    "areverse,"
    "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.15,"
    "areverse"
)

# What each model's tokenizer expects (sample rate, channels).
FORMATS = {
    "24k_mono": (24000, 1),  # MOSS-TTS v1.5 8B and Qwen3-TTS
    "48k_stereo": (48000, 2),  # MOSS-TTS-Local-Transformer v1.5 (MOSS-Audio-Tokenizer-v2)
}


def prepare_voice(src: Path, name: str, transcript: str | None, voices_dir: Path) -> dict:
    """Trim silence, clean up, loudness-normalize to -20 LUFS and write per-model copies.

    Never touches the source file; everything goes into voices_dir/name/.
    """
    out_dir = voices_dir / name
    out_dir.mkdir(parents=True, exist_ok=True)
    trimmed = out_dir / "trimmed.wav"
    ffmpeg("-i", str(src), "-af", f"{TRIM},highpass=f=60", "-ac", "1", "-ar", "48000",
           "-c:a", "pcm_f32le", str(trimmed))

    m = loudnorm_measure(trimmed, -20, -2)
    norm = (
        f"loudnorm=I=-20:TP=-2:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
        f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
        f"offset={m['target_offset']}:linear=true,"
        "apad=pad_dur=0.25,adelay=250:all=1"
    )
    files = {}
    for label, (sr, ch) in FORMATS.items():
        dst = out_dir / f"ref_{label}.wav"
        ffmpeg("-i", str(trimmed), "-af", norm, "-ar", str(sr), "-ac", str(ch),
               "-c:a", "pcm_s16le", str(dst))
        files[label] = str(dst)
    trimmed.unlink()

    seconds = duration(files["24k_mono"])
    info = {
        "name": name,
        "source": str(src),
        "transcript": transcript,
        "seconds": round(seconds, 1),
        "files": files,
    }
    warnings = []
    if seconds < 8:
        warnings.append("Clip is shorter than 8 s; cloning will be less stable. Aim for 10-30 s.")
    if seconds > 35:
        warnings.append("Clip is longer than 35 s; consider trimming to 10-30 s.")
    if not transcript:
        warnings.append("No transcript given; Qwen3-TTS will clone from audio only (lower quality).")
    info["warnings"] = warnings
    (out_dir / "voice.yaml").write_text(yaml.safe_dump(info, sort_keys=False, allow_unicode=True))
    return info


def load_voice(name_or_dir: str, voices_dir: Path) -> dict:
    path = Path(name_or_dir).expanduser()
    if not path.exists():
        path = voices_dir / name_or_dir
    return yaml.safe_load((path / "voice.yaml").read_text())


def ref_for_model(voice: dict, family_repo: str) -> str:
    """Pick the reference file whose format matches the model."""
    if "local-transformer" in family_repo.lower():
        return voice["files"]["48k_stereo"]
    return voice["files"]["24k_mono"]
