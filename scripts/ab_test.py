"""Listening test: render the same ~2 minute passage with every model, voice and setting.

Usage:
  uv run python scripts/ab_test.py voices          # design two narrator voices + reference clips
  uv run python scripts/ab_test.py run MODEL       # moss8b | mosslocal | qwen3 | qwen3-custom | qwen3-design
  uv run python scripts/ab_test.py report          # transcribe everything, write ab_test/RESULTS.md

Outputs go to ab_test/ with names like 03_moss8b_designmale_card.wav.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import mlx.core as mx  # noqa: E402
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

from abtts.audio import silence  # noqa: E402
from abtts.engines import Engine, Voice  # noqa: E402
from abtts.voice import load_voice, prepare_voice, ref_for_model  # noqa: E402

AB_DIR = ROOT / "ab_test"
VOICES_DIR = ROOT / "voices"
SEED = 20261021
PARAGRAPH_GAP = 0.7

PASSAGE = [
    "On Tuesday, the 14th of March 1923, at precisely 7:45 in the morning, Professor Aoife "
    "Szczepańska stepped down from the night train at Carrow Junction with £250 in her coat, "
    "two trunks of instruments, and a letter of introduction that nobody at the station "
    "seemed able to read.",
    "“You’ll be wanting the observatory, then,” said the stationmaster, squinting at her "
    "luggage. “It’s 3 miles up the hill, and the road’s been out since February.” “Then I "
    "shall walk,” she replied. “I have walked further for less.”",
    "The road, when she finally found it, wound upward through a forest of black pines so old "
    "and so densely planted that the light beneath them seemed to come from nowhere in "
    "particular, past a ruined chapel whose roof had fallen in sometime during the reign of "
    "Queen Victoria, past a farmhouse where a dog barked at her without much conviction, and "
    "past a milestone so worn by weather that she could make out only the number 1 and, "
    "beneath it, what might once have been the name of a town.",
    "The observatory had been built in 1887 at a cost of 4,312 pounds, and its great "
    "telescope, a 24-inch refractor, weighed nearly 2.5 tons. According to the logbook, the "
    "last recorded observation had been made on 31 December 1919, at 11:58 p.m., two minutes "
    "before the new decade began.",
    "Mr. Hollis, the caretaker, met her at the gate. He was 78 years old, he told her, and had "
    "worked there for 52 of them. “Nobody’s looked through that glass in 4 years,” he said. "
    "“Not since the old professor died. You’re the 1st woman to try.”",
    "She smiled, set down her trunks, and asked him to show her the dome. Somewhere above the "
    "clouds, she knew, Jupiter was rising, and she intended to be there to meet it.",
]

REFERENCE_TEXT = (
    "There is a particular kind of quiet that settles over a house late at night, when the "
    "last of the lights are out and the clocks seem louder than they did during the day. It "
    "is in that quiet, I have always thought, that the best stories are told."
)

DESIGNED_VOICES = {
    "designmale": "A warm, mature male narrator in his fifties with a low, gentle, slightly "
    "husky voice and a neutral American accent. Calm, unhurried, intimate audiobook delivery.",
    "designfemale": "A calm, warm female narrator in her thirties with a clear, smooth voice "
    "and a neutral American accent. Measured pace, soft and expressive audiobook delivery.",
}

MOSS_CARD = {"audio_temperature": 1.7, "audio_top_p": 0.8, "audio_top_k": 25, "audio_repetition_penalty": 1.0}
# "lower values stabilize prosody" (MOSS-TTS 1.0 model card, generation hyperparameters)
MOSS_STEADY = {"audio_temperature": 1.3, "audio_top_p": 0.8, "audio_top_k": 25, "audio_repetition_penalty": 1.0}
# MossTTSLocal recommended row in the MOSS-TTS 1.0 card
MOSS_LOCAL_V10 = {"audio_temperature": 1.0, "audio_top_p": 0.95, "audio_top_k": 50, "audio_repetition_penalty": 1.1}
QWEN_CARD = {"temperature": 0.9, "top_k": 50, "top_p": 1.0, "repetition_penalty": 1.05}
QWEN_STEADY = {"temperature": 0.7, "top_k": 50, "top_p": 1.0, "repetition_penalty": 1.05}

# model -> list of (voice, setting name, sampling)
PLAN = {
    "moss8b": [
        ("designmale", "card", MOSS_CARD),
        ("designmale", "steady", MOSS_STEADY),
        ("designfemale", "card", MOSS_CARD),
        ("designfemale", "steady", MOSS_STEADY),
        ("default", "card", MOSS_CARD),
    ],
    "mosslocal": [
        ("designmale", "card", MOSS_CARD),
        ("designmale", "v10local", MOSS_LOCAL_V10),
        ("designfemale", "card", MOSS_CARD),
        ("designfemale", "v10local", MOSS_LOCAL_V10),
    ],
    "qwen3": [
        ("designmale", "card", QWEN_CARD),
        ("designmale", "steady", QWEN_STEADY),
        ("designfemale", "card", QWEN_CARD),
        ("designfemale", "steady", QWEN_STEADY),
    ],
    "qwen3-custom": [
        ("preset:Ryan", "card", QWEN_CARD),
        ("preset:Aiden", "card", QWEN_CARD),
    ],
    "qwen3-design": [
        ("design:designmale", "card", QWEN_CARD),
        ("design:designfemale", "card", QWEN_CARD),
    ],
}
ORDER = list(PLAN)


def make_voices():
    raw_dir = AB_DIR / "voices_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    engine = Engine("qwen3-design")
    for name, description in DESIGNED_VOICES.items():
        engine.voice = Voice(instruct=description)
        audio, sr = engine.synth(REFERENCE_TEXT, seed=SEED)
        raw = raw_dir / f"{name}.wav"
        sf.write(raw, audio, sr)
        info = prepare_voice(raw, name, REFERENCE_TEXT, VOICES_DIR)
        print(name, info["seconds"], "s", info["warnings"])


def voice_for(engine: Engine, voice_key: str) -> Voice:
    if voice_key == "default":
        return Voice()
    if voice_key.startswith("preset:"):
        return Voice(speaker=voice_key.split(":", 1)[1])
    if voice_key.startswith("design:"):
        return Voice(instruct=DESIGNED_VOICES[voice_key.split(":", 1)[1]])
    info = load_voice(voice_key, VOICES_DIR)
    return Voice(ref_audio=ref_for_model(info, engine.repo), ref_text=info["transcript"])


def run_model(model: str):
    engine = Engine(model)
    t0 = time.perf_counter()
    engine.load()
    load_s = time.perf_counter() - t0
    idx = ORDER.index(model)
    for n, (voice_key, setting, sampling) in enumerate(PLAN[model]):
        engine.voice = voice_for(engine, voice_key)
        engine.sampling = dict(sampling)
        mx.reset_peak_memory()
        pieces, gen_s, audio_s, chunk_seconds = [], 0.0, 0.0, []
        for para in PASSAGE:
            t = time.perf_counter()
            audio, sr = engine.synth(para, seed=SEED)
            gen_s += time.perf_counter() - t
            audio_s += len(audio) / sr
            chunk_seconds.append(round(len(audio) / sr, 2))
            pieces += [audio, silence(PARAGRAPH_GAP, sr)]
        vname = voice_key.replace("preset:", "").replace("design:", "vd-")
        stem = f"{idx + 1}{chr(ord('a') + n)}_{model}_{vname}_{setting}"
        wav = AB_DIR / f"{stem}.wav"
        sf.write(wav, np.concatenate(pieces), sr)
        meta = {
            "file": wav.name, "model": model, "repo": engine.repo, "voice": voice_key,
            "setting": setting, "sampling": sampling, "seed": SEED, "sample_rate": sr,
            "audio_seconds": round(audio_s, 1), "generation_seconds": round(gen_s, 1),
            "rtf": round(gen_s / audio_s, 3), "load_seconds": round(load_s, 1),
            "mlx_peak_memory_gb": round(mx.get_peak_memory() / 1e9, 2),
            "chunk_seconds": chunk_seconds,
        }
        (AB_DIR / f"{stem}.json").write_text(json.dumps(meta, indent=2))
        print(f"{wav.name}: {audio_s:.0f}s audio, RTF {meta['rtf']}", flush=True)


def report():
    import jiwer

    from abtts.qa import Transcriber, normalize_for_wer, word_error_rate

    stt = Transcriber()
    reference = " ".join(PASSAGE)
    rows = []
    for meta_path in sorted(AB_DIR.glob("*_*.json")):
        meta = json.loads(meta_path.read_text())
        if "transcript" not in meta:
            meta["transcript"] = stt.transcribe(AB_DIR / meta["file"])
            meta_path.write_text(json.dumps(meta, indent=2))
        meta["wer"] = word_error_rate(reference, meta["transcript"])
        ref_n, hyp_n = normalize_for_wer(reference), normalize_for_wer(meta["transcript"])
        diffs = []
        for c in jiwer.process_words(ref_n, hyp_n).alignments[0]:
            if c.type != "equal":
                r = " ".join(ref_n.split()[c.ref_start_idx:c.ref_end_idx])
                h = " ".join(hyp_n.split()[c.hyp_start_idx:c.hyp_end_idx])
                diffs.append(f"{r or '∅'} → {h or '∅'}")
        meta["diffs"] = diffs
        rows.append(meta)

    lines = [
        "# A/B listening test results", "",
        f"Passage: {len(' '.join(PASSAGE).split())} words, 6 paragraphs, seed {SEED}. "
        "RTF = generation time ÷ audio length (lower is faster). "
        "10-hour book = RTF × 10 h of generation (plus about 10% for QA and retries).", "",
        "| File | Model | Voice | Settings | RTF | 10 h book | WER | MLX peak |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for m in rows:
        s = m["sampling"]
        settings = m["setting"] + " (" + ", ".join(f"{k.replace('audio_', '')}={v}" for k, v in s.items()) + ")"
        hours = m["rtf"] * 10
        lines.append(
            f"| {m['file']} | {m['model']} | {m['voice']} | {settings} | {m['rtf']:.2f} | "
            f"{hours:.1f} h | {m['wer']:.1%} | {m['mlx_peak_memory_gb']} GB |"
        )
    lines += ["", "## Where each file differed from the text (after normalization)", ""]
    for m in rows:
        lines.append(f"- **{m['file']}**: " + ("; ".join(m["diffs"]) or "no differences"))
    (AB_DIR / "RESULTS.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "voices":
        make_voices()
    elif cmd == "run":
        run_model(sys.argv[2])
    elif cmd == "report":
        report()
