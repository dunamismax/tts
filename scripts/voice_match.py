"""Compare narration delivery against a voice's demo clip (the sample on the Voices page).

Usage:
  uv run python scripts/voice_match.py measure WAV [WAV ...]
  uv run python scripts/voice_match.py sweep VOICE [--temps 0.6,0.7,0.8,0.9] [--seeds 3]

Features (speech only, measured the same way for every file):
  wpm           words per minute over the whole clip
  artic         articulation rate: words per minute of voiced time (excludes pauses)
  pause_ratio   share of the clip that is pause (quieter than 35 dB below the loudest speech)
  mean_pause    average length of pauses longer than 0.15 s
  f0            median pitch in Hz, f0_range = 10th-90th percentile spread in semitones (expressiveness)
  centroid      spectral centroid in Hz (brightness)
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

OUT = ROOT / "ab_test" / "voice_match"


def load(path: str | Path, sr_target: int = 24000) -> np.ndarray:
    audio, sr = sf.read(str(path), dtype="float64", always_2d=True)
    audio = audio.mean(axis=1)
    if sr != sr_target:
        from scipy.signal import resample_poly

        g = np.gcd(sr, sr_target)
        audio = resample_poly(audio, sr_target // g, sr // g)
    return audio


def pitch_track(x: np.ndarray, sr: int, fmin=60.0, fmax=300.0, frame=0.04, hop=0.01, threshold=0.12) -> np.ndarray:
    """YIN pitch tracker (de Cheveigne & Kawahara 2002); returns F0 of voiced frames in Hz."""
    n, h = int(frame * sr), int(hop * sr)
    tau_min, tau_max = int(sr / fmax), int(sr / fmin)
    out = []
    for start in range(0, len(x) - n - tau_max, h):
        seg = x[start:start + n + tau_max]
        if np.sqrt(np.mean(seg[:n] ** 2)) < 3e-3:
            continue
        # difference function via FFT autocorrelation
        w = n
        xf = np.fft.rfft(seg, 2 * len(seg))
        acf = np.fft.irfft(xf * np.conj(xf))[: tau_max + 1]
        energy = np.cumsum(np.concatenate([[0.0], seg ** 2]))
        e0 = energy[w] - energy[0]
        taus = np.arange(tau_max + 1)
        e_tau = energy[taus + w] - energy[taus]
        d = e0 + e_tau - 2 * acf
        d[0] = 0
        cmnd = d[1:] * np.arange(1, tau_max + 1) / np.maximum(np.cumsum(d[1:]), 1e-12)
        cmnd = np.concatenate([[1.0], cmnd])
        cand = np.nonzero(cmnd[tau_min:] < threshold)[0]
        if cand.size == 0:
            continue
        tau = tau_min + cand[0]
        while tau + 1 <= tau_max and cmnd[tau + 1] < cmnd[tau]:
            tau += 1
        if 1 <= tau < tau_max:  # parabolic interpolation
            a, b, c = cmnd[tau - 1], cmnd[tau], cmnd[tau + 1]
            denom = a - 2 * b + c
            tau = tau + 0.5 * (a - c) / denom if denom else tau
        out.append(sr / tau)
    return np.array(out)


def features(path: str | Path, words: int) -> dict:
    sr = 24000
    x = load(path, sr)
    win = int(0.02 * sr)
    frames = len(x) // win
    rms = np.sqrt(np.mean(x[: frames * win].reshape(frames, win) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    speech = db > (np.percentile(db, 95) - 35)
    # trim leading/trailing silence
    idx = np.nonzero(speech)[0]
    speech = speech[idx[0]: idx[-1] + 1]
    total = len(speech) * 0.02
    voiced = speech.sum() * 0.02
    pauses, run = [], 0
    for s in speech:
        if not s:
            run += 1
        elif run:
            if run * 0.02 >= 0.15:
                pauses.append(run * 0.02)
            run = 0
    f0 = pitch_track(x[idx[0] * win: (idx[-1] + 1) * win], sr)
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    freqs = np.fft.rfftfreq(len(x), 1 / sr)
    centroid = float((spec * freqs).sum() / spec.sum())
    p10, p50, p90 = np.percentile(f0, [10, 50, 90]) if f0.size else (0, 0, 0)
    return {
        "seconds": round(total, 2),
        "wpm": round(words / total * 60, 1),
        "artic": round(words / voiced * 60, 1),
        "pause_ratio": round(1 - voiced / total, 3),
        "mean_pause": round(statistics.mean(pauses), 3) if pauses else 0.0,
        "pauses": len(pauses),
        "f0": round(float(p50), 1),
        "f0_range": round(float(12 * np.log2(p90 / p10)), 2) if p10 else 0.0,
        "centroid": round(centroid),
    }


def distance(a: dict, ref: dict) -> float:
    """Relative difference on the features that define delivery; pace weighted most."""
    terms = [
        2.0 * abs(a["wpm"] - ref["wpm"]) / ref["wpm"],
        1.5 * abs(a["artic"] - ref["artic"]) / ref["artic"],
        1.0 * abs(a["pause_ratio"] - ref["pause_ratio"]) / max(ref["pause_ratio"], 0.05),
        1.0 * abs(a["f0"] - ref["f0"]) / ref["f0"],
        1.0 * abs(a["f0_range"] - ref["f0_range"]) / max(ref["f0_range"], 1),
        0.5 * abs(a["centroid"] - ref["centroid"]) / ref["centroid"],
    ]
    return round(sum(terms), 3)


def sweep(voice: str, temps: list[float], seeds: int, text: str, tag: str):
    from abtts.engines import Engine, Voice
    from abtts.render import trim_edges
    from abtts.voice import load_voice

    info = load_voice(voice, ROOT / "voices")
    ref_path = info["files"]["24k_mono"]
    ref = features(ref_path, len(info["transcript"].split()))
    engine = Engine("mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16",
                    voice=Voice(ref_audio=ref_path, ref_text=info["transcript"]))
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for t in temps:
        engine.sampling = {**engine.sampling, "temperature": t}
        for s in range(seeds):
            audio, sr = engine.synth(text, seed=20261021 + s)
            audio = trim_edges(audio, sr)
            wav = OUT / f"{voice}_{tag}_t{t}_s{s}.wav"
            sf.write(wav, audio, sr)
            f = features(wav, len(text.split()))
            f.update({"temp": t, "seed": s, "file": wav.name, "dist": distance(f, ref)})
            rows.append(f)
            print(json.dumps(f), flush=True)
    return ref, rows


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure")
    m.add_argument("wavs", nargs="+")
    m.add_argument("--words", type=int, required=True)
    s = sub.add_parser("sweep")
    s.add_argument("voice")
    s.add_argument("--temps", default="0.6,0.7,0.8,0.9")
    s.add_argument("--seeds", type=int, default=3)
    s.add_argument("--text", choices=["reference", "book"], default="reference")
    args = ap.parse_args()

    if args.cmd == "measure":
        for w in args.wavs:
            print(Path(w).name, json.dumps(features(w, args.words)))
        return

    from abtts.voice import load_voice

    info = load_voice(args.voice, ROOT / "voices")
    if args.text == "reference":
        text = info["transcript"]
    else:
        text = ("High above the city, on a tall column, stood the statue of the Happy Prince. He was gilded "
                "all over with thin leaves of fine gold, for eyes he had two bright sapphires, and a large red "
                "ruby glowed on his sword-hilt. He was very much admired indeed. \"He is as beautiful as a "
                "weathercock,\" remarked one of the Town Councillors who wished to gain a reputation for having "
                "artistic tastes; \"only not quite so useful,\" he added, fearing lest people should think him "
                "unpractical, which he really was not.")
    ref, rows = sweep(args.voice, [float(t) for t in args.temps.split(",")], args.seeds, text, args.text)
    summary = {}
    for t in sorted({r["temp"] for r in rows}):
        rs = [r for r in rows if r["temp"] == t]
        summary[t] = {k: round(statistics.mean(r[k] for r in rs), 3) for k in
                      ("wpm", "artic", "pause_ratio", "mean_pause", "f0", "f0_range", "centroid", "dist")}
    result = {"voice": args.voice, "text": args.text, "reference": ref, "by_temperature": summary, "runs": rows}
    (OUT / f"{args.voice}_{args.text}.json").write_text(json.dumps(result, indent=2))
    print("REFERENCE", json.dumps(ref))
    for t, s_ in summary.items():
        print(f"temp {t}: {json.dumps(s_)}")


if __name__ == "__main__":
    main()
