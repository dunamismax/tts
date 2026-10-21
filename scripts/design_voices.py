"""Design narrator voices with Qwen3 VoiceDesign and save them as reusable reference clips.

Usage: uv run python scripts/design_voices.py [NAME ...]

Each voice gets several takes of REFERENCE_TEXT. The take with the lowest word error
rate (ties: pace closest to 155 words per minute) becomes voices/NAME/, with the
transcript stored for Qwen3-TTS cloning. All takes are kept in ab_test/voices_raw/.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import soundfile as sf  # noqa: E402

from abtts.engines import Engine, Voice  # noqa: E402
from abtts.qa import Transcriber, word_error_rate  # noqa: E402
from abtts.voice import prepare_voice  # noqa: E402

VOICES_DIR = ROOT / "voices"
RAW_DIR = ROOT / "ab_test" / "voices_raw"
TAKES = 3
TARGET_WPM = 155

REFERENCE_TEXT = (
    "It was late in the evening when the letter finally arrived. She turned it over twice "
    "before opening it, as if the envelope itself might tell her something. \"Well,\" she said "
    "quietly, \"I suppose we had better see what it says.\" Outside, the rain had softened to a "
    "whisper, and somewhere down the lane a dog was barking at nothing at all."
)

DESCRIPTIONS = {
    "deepbaritone": (
        "A deep, rich baritone male narrator in his sixties with a warm, resonant, slightly "
        "gravelly voice and a neutral American accent. Slow, calm, authoritative storytelling, "
        "like a classic audiobook narrator."
    ),
    "britishmale": (
        "A mature British male narrator in his fifties with a warm, refined Received "
        "Pronunciation accent and a smooth, mellow low-mid voice. Gentle, measured, intimate "
        "audiobook delivery."
    ),
    "warmfemale": (
        "A warm, mature female narrator in her forties with a smooth, rich low-mid voice and a "
        "neutral American accent. Calm, intimate, expressive audiobook delivery."
    ),
}


def main(names: list[str]):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    engine = Engine("qwen3-design")
    takes: dict[str, list[Path]] = {}
    for name in names:
        engine.voice = Voice(instruct=DESCRIPTIONS[name])
        takes[name] = []
        for t in range(TAKES):
            audio, sr = engine.synth(REFERENCE_TEXT, seed=1000 + t)
            path = RAW_DIR / f"{name}_take{t + 1}.wav"
            sf.write(path, audio, sr)
            takes[name].append(path)
    engine.unload()

    stt = Transcriber()
    words = len(REFERENCE_TEXT.split())
    for name, paths in takes.items():
        scored = []
        for path in paths:
            info = sf.info(path)
            wpm = words / (info.frames / info.samplerate / 60)
            wer = word_error_rate(REFERENCE_TEXT, stt.transcribe(path))
            scored.append((wer, abs(wpm - TARGET_WPM), path, wpm))
            print(f"{path.name}: WER {wer:.1%}, {wpm:.0f} wpm")
        wer, _, best, wpm = min(scored)
        result = prepare_voice(best, name, REFERENCE_TEXT, VOICES_DIR)
        print(f"-> {name}: {best.name} ({result['seconds']} s, {wpm:.0f} wpm) {result['warnings']}")


if __name__ == "__main__":
    main(sys.argv[1:] or list(DESCRIPTIONS))
