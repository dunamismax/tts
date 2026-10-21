"""Fit tempo, pause stretch and tone EQ so cloned narration matches a voice's demo clip.

Usage: uv run python scripts/delivery_fit.py VOICE [--write]

Uses the clone renders of the demo's own transcript from scripts/voice_match.py
(ab_test/voice_match/VOICE_reference_t*_s*.wav) at the voice's chosen temperature, tries a
grid of tempo x pause-stretch settings, and reports the closest match to the demo on
articulation rate, pause share, mean pause length and words per minute. --write saves the
result as `delivery:` in voices/VOICE/voice.yaml.
"""

import argparse
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
import yaml  # noqa: E402

from abtts.audio import ffmpeg, stretch_pauses, tempo_filter  # noqa: E402
from abtts.voice import load_voice  # noqa: E402
from scripts.ltas import match_curve  # noqa: E402
from scripts.voice_match import features  # noqa: E402

OUT = ROOT / "ab_test" / "voice_match" / "fit"


def score(f, ref):
    return (2.0 * abs(f["artic"] - ref["artic"]) / ref["artic"]
            + 1.5 * abs(f["pause_ratio"] - ref["pause_ratio"]) / ref["pause_ratio"]
            + 1.0 * abs(f["mean_pause"] - ref["mean_pause"]) / ref["mean_pause"]
            + 1.0 * abs(f["wpm"] - ref["wpm"]) / ref["wpm"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("voice")
    ap.add_argument("--temperature", type=float, default=0.9)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--tempo", type=float, help="pin the tempo instead of taking the best score")
    ap.add_argument("--pause", type=float, help="pin the pause stretch instead of taking the best score")
    ap.add_argument("--pitch", type=float, default=0.0, help="pitch shift in semitones (e.g. -1)")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    info = load_voice(args.voice, ROOT / "voices")
    demo = info["files"]["24k_mono"]
    words = len(info["transcript"].split())
    ref = features(demo, words)
    takes = sorted((ROOT / "ab_test" / "voice_match").glob(f"{args.voice}_reference_t{args.temperature}_s*.wav"))
    if not takes:
        sys.exit("Run scripts/voice_match.py sweep first.")

    results = []
    for tempo, pause in itertools.product([1.0, 0.95, 0.92, 0.90, 0.88, 0.86], [1.0, 1.15, 1.3, 1.45, 1.6]):
        feats = []
        for k, t in enumerate(takes):
            audio, sr = sf.read(str(t), dtype="float32")
            shaped = OUT / f"tmp_{k}.wav"
            sf.write(shaped, stretch_pauses(audio, sr, pause), sr)
            out = OUT / f"fit_{k}.wav"
            filt = tempo_filter(tempo, args.pitch, sr).rstrip(",") or "anull"
            ffmpeg("-i", str(shaped), "-af", filt, str(out))
            feats.append(features(out, words))
        mean = {k: float(np.mean([f[k] for f in feats])) for k in ("wpm", "artic", "pause_ratio", "mean_pause")}
        results.append((score(mean, ref), tempo, pause, mean))
    results.sort(key=lambda r: r[0])
    print("demo:", {k: ref[k] for k in ("wpm", "artic", "pause_ratio", "mean_pause")})
    for s, tempo, pause, m in results[:6]:
        print(f"score {s:.3f}  tempo {tempo}  pause x{pause}  ->", {k: round(v, 3) for k, v in m.items()})
    best = results[0]
    if args.tempo or args.pause:
        pinned = [r for r in results if (not args.tempo or r[1] == args.tempo) and (not args.pause or r[2] == args.pause)]
        best = pinned[0] if pinned else best
        print(f"using tempo {best[1]}, pause x{best[2]} ->", {k: round(v, 3) for k, v in best[3].items()})
    # Fit the tone EQ on takes processed with the chosen delivery (pause, pitch, tempo),
    # since lowering pitch also shifts the spectrum down a little.
    processed = []
    for k, t in enumerate(takes):
        audio, sr = sf.read(str(t), dtype="float32")
        shaped = OUT / f"eqfit_in_{k}.wav"
        sf.write(shaped, stretch_pauses(audio, sr, best[2]), sr)
        out = OUT / f"eqfit_{k}.wav"
        ffmpeg("-i", str(shaped), "-af", tempo_filter(best[1], args.pitch, sr).rstrip(",") or "anull", "-ar", str(sr), str(out))
        processed.append(out)
    eq = match_curve(demo, processed, strength=1.0)
    print("tone EQ:", eq)
    if args.write:
        vf = ROOT / "voices" / args.voice / "voice.yaml"
        data = yaml.safe_load(vf.read_text())
        data["delivery"] = {
            "temperature": args.temperature,
            "tempo": best[1],
            "pitch": args.pitch,
            "pause_stretch": best[2],
            "eq": eq,
            "note": "Fitted by scripts/delivery_fit.py so narration matches this voice's demo clip.",
        }
        vf.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
        print(f"wrote delivery settings to {vf}")


if __name__ == "__main__":
    main()
