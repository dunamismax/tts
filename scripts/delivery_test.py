"""Which narration path best reproduces a voice's demo clip on real book text?

Usage: uv run python scripts/delivery_test.py VOICE BOOK [--paras 8]

A  clone:  Qwen3 Base cloning the demo clip (the normal pipeline)
B  design: Qwen3 VoiceDesign reading directly with the voice's original description and seed

Per paragraph: speaker similarity to the demo (Qwen3 speaker encoder), pace and pause
features. Results: ab_test/delivery/.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import mlx.core as mx  # noqa: E402
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

from abtts.books import read_book  # noqa: E402
from abtts.engines import Engine, Voice  # noqa: E402
from abtts.render import trim_edges  # noqa: E402
from abtts.textnorm import normalize_for_tts  # noqa: E402
from abtts.voice import load_voice  # noqa: E402
from scripts.design_voices import DESCRIPTIONS  # noqa: E402
from scripts.voice_match import distance, features, load  # noqa: E402

OUT = ROOT / "ab_test" / "delivery"
DESIGN_SEED = {"britishmale": 1002, "deepbaritone": 1002, "warmfemale": 1000}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("voice")
    ap.add_argument("book")
    ap.add_argument("--paras", type=int, default=8)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    info = load_voice(args.voice, ROOT / "voices")
    demo = info["files"]["24k_mono"]
    book = read_book(Path(args.book))
    paras = [normalize_for_tts(p) for p in book.chapters[0]["paragraphs"] if len(p) > 120][: args.paras]

    paths = {"clone": [], "design": []}
    clone = Engine("mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16", voice=Voice(ref_audio=demo, ref_text=info["transcript"]))
    for i, text in enumerate(paras):
        audio, sr = clone.synth(text, seed=20261021)
        p = OUT / f"{args.voice}_clone_{i:02d}.wav"
        sf.write(p, trim_edges(audio, sr), sr)
        paths["clone"].append(p)
    clone.unload()
    design = Engine("qwen3-design", voice=Voice(instruct=DESCRIPTIONS[args.voice]))
    for i, text in enumerate(paras):
        audio, sr = design.synth(text, seed=DESIGN_SEED.get(args.voice, 1000))
        p = OUT / f"{args.voice}_design_{i:02d}.wav"
        sf.write(p, trim_edges(audio, sr), sr)
        paths["design"].append(p)
    design.unload()

    from mlx_audio.tts import load as tts_load

    base = tts_load("mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16", lazy=True)

    def embed(path):
        e = np.array(base.extract_speaker_embedding(mx.array(load(path, 24000).astype(np.float32))), dtype=np.float32).reshape(-1)
        return e / np.linalg.norm(e)

    demo_e = embed(demo)
    ref = features(demo, len(info["transcript"].split()))
    result = {"reference": ref}
    for kind, ps in paths.items():
        sims = [float(demo_e @ embed(p)) for p in ps]
        embs = [embed(p) for p in ps]
        consistency = [float(embs[i] @ embs[j]) for i in range(len(embs)) for j in range(i + 1, len(embs))]
        feats = [features(p, len(t.split())) for p, t in zip(ps, paras)]
        mean = {k: round(statistics.mean(f[k] for f in feats), 3) for k in ("wpm", "artic", "pause_ratio", "mean_pause", "f0", "f0_range")}
        result[kind] = {
            "similarity_to_demo": {"min": round(min(sims), 3), "mean": round(statistics.mean(sims), 3)},
            "chunk_to_chunk": {"min": round(min(consistency), 3), "mean": round(statistics.mean(consistency), 3)},
            "features": mean, "per_chunk_sim": [round(s, 3) for s in sims],
            "distance_to_demo": round(statistics.mean(distance(f, ref) for f in feats), 3),
        }
    (OUT / f"{args.voice}_results.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
