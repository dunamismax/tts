"""Qwen3-TTS tuning experiments on the A/B passage.

Usage:
  uv run python scripts/qwen_tune.py run GROUP     # base | custom
  uv run python scripts/qwen_tune.py score         # WER + speaker similarity -> ab_test/tune/TUNE.md

Each variant changes one thing (text normalization, temperature, chunk size, style
instruction) so its effect can be heard and measured.
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
from abtts.chunking import chunk_paragraph  # noqa: E402
from abtts.engines import Engine, Voice  # noqa: E402
from abtts.textnorm import normalize_for_tts  # noqa: E402
from abtts.voice import load_voice  # noqa: E402
from scripts.ab_test import PASSAGE, SEED, VOICES_DIR  # noqa: E402

OUT = ROOT / "ab_test" / "tune"
NARRATE = "Calm, warm, measured audiobook narration with natural pauses."

# name -> spec
VARIANTS = {
    "base": {
        "t1_raw_t09_para": dict(voice="designmale", norm=False, temp=0.9, max_chars=10_000),
        "t2_norm_t09_para": dict(voice="designmale", norm=True, temp=0.9, max_chars=10_000),
        "t3_norm_t07_para": dict(voice="designmale", norm=True, temp=0.7, max_chars=10_000),
        "t4_norm_t08_para": dict(voice="designmale", norm=True, temp=0.8, max_chars=10_000),
        "t5_norm_t09_c250": dict(voice="designmale", norm=True, temp=0.9, max_chars=250),
        "t6_norm_t09_whole": dict(voice="designmale", norm=True, temp=0.9, max_chars=10_000, whole=True),
    },
    "custom": {
        "c1_ryan_norm": dict(speaker="Ryan", norm=True, temp=0.9, max_chars=10_000),
        "c2_ryan_norm_instr": dict(speaker="Ryan", norm=True, temp=0.9, max_chars=10_000, instruct=NARRATE),
        "c3_aiden_norm": dict(speaker="Aiden", norm=True, temp=0.9, max_chars=10_000),
        "c4_aiden_norm_instr": dict(speaker="Aiden", norm=True, temp=0.9, max_chars=10_000, instruct=NARRATE),
    },
}


def render(engine: Engine, name: str, spec: dict):
    paragraphs = [normalize_for_tts(p) if spec["norm"] else p for p in PASSAGE]
    if spec.get("whole"):
        groups = [[" ".join(paragraphs)]]
    else:
        groups = [chunk_paragraph(p, spec["max_chars"]) for p in paragraphs]
    engine.sampling = {**engine.sampling, "temperature": spec["temp"]}
    pieces, chunk_meta, gen_s = [], [], 0.0
    for gi, group in enumerate(groups):
        for ci, text in enumerate(group):
            t = time.perf_counter()
            audio, sr = engine.synth(text, seed=SEED)
            gen_s += time.perf_counter() - t
            chunk_meta.append({"text": text, "seconds": round(len(audio) / sr, 2), "start": sum(len(p) for p in pieces) / sr})
            pieces.append(audio)
            pieces.append(silence(0.25 if ci < len(group) - 1 else 0.7, sr))
    audio = np.concatenate(pieces)
    sf.write(OUT / f"{name}.wav", audio, sr)
    secs = sum(c["seconds"] for c in chunk_meta)
    meta = {"name": name, "spec": spec, "seed": SEED, "sample_rate": sr, "chunks": chunk_meta,
            "audio_seconds": round(secs, 1), "rtf": round(gen_s / secs, 3)}
    (OUT / f"{name}.json").write_text(json.dumps(meta, indent=2))
    print(f"{name}: {secs:.0f}s, RTF {meta['rtf']}", flush=True)


def run(group: str):
    OUT.mkdir(parents=True, exist_ok=True)
    model = "qwen3" if group == "base" else "qwen3-custom"
    engine = Engine(model)
    for name, spec in VARIANTS[group].items():
        if "voice" in spec:
            info = load_voice(spec["voice"], VOICES_DIR)
            engine.voice = Voice(ref_audio=info["files"]["24k_mono"], ref_text=info["transcript"])
        else:
            engine.voice = Voice(speaker=spec["speaker"], instruct=spec.get("instruct"))
        render(engine, name, spec)


def speaker_similarity(wav_paths_and_spans, reference_wav: str | None):
    """Cosine similarity of each chunk's speaker embedding to the reference (or to chunk 1)."""
    from mlx_audio.tts import load
    from mlx_audio.utils import load_audio

    base = load("mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16", lazy=True)

    def embed(audio):
        e = np.array(base.extract_speaker_embedding(mx.array(audio)), dtype=np.float32).reshape(-1)
        return e / np.linalg.norm(e)

    results = {}
    ref_e = embed(np.array(load_audio(reference_wav, sample_rate=24000))) if reference_wav else None
    for name, (wav, spans) in wav_paths_and_spans.items():
        audio = np.array(load_audio(str(wav), sample_rate=24000))
        embs = [embed(audio[int(s * 24000): int((s + d) * 24000)]) for s, d in spans]
        anchor = ref_e if ref_e is not None and "ref" in name else embs[0]
        sims = [float(anchor @ e) for e in embs]
        results[name] = sims
    return results


def score():
    import jiwer  # noqa: F401

    from abtts.qa import Transcriber, word_error_rate

    reference = " ".join(PASSAGE)
    stt = Transcriber()
    metas = [json.loads(p.read_text()) for p in sorted(OUT.glob("*.json"))]
    for m in metas:
        if "transcript" not in m:
            m["transcript"] = stt.transcribe(OUT / f"{m['name']}.wav")
        m["wer"] = word_error_rate(reference, m["transcript"])
    stt.unload()

    ref_wav = load_voice("designmale", VOICES_DIR)["files"]["24k_mono"]
    spans = {}
    for m in metas:
        key = m["name"] + ("_ref" if "voice" in m["spec"] else "")
        spans[key] = (OUT / f"{m['name']}.wav", [(c["start"], c["seconds"]) for c in m["chunks"]])
    sims = speaker_similarity(spans, ref_wav)
    rows = ["| Variant | Chunks | RTF | WER | Voice similarity (min / mean) |", "|---|---:|---:|---:|---|"]
    for m in metas:
        key = m["name"] + ("_ref" if "voice" in m["spec"] else "")
        s = sims[key]
        m["similarity"] = s
        (OUT / f"{m['name']}.json").write_text(json.dumps(m, indent=2))
        rows.append(f"| {m['name']} | {len(m['chunks'])} | {m['rtf']:.2f} | {m['wer']:.1%} | {min(s):.3f} / {np.mean(s):.3f} |")
    text = "\n".join(rows)
    (OUT / "TUNE.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(sys.argv[2])
    else:
        score()
