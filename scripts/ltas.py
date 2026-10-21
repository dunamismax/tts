"""Long-term average spectrum (speech frames only) in bands, relative to the 500-1000 Hz band.

Usage: uv run python scripts/ltas.py REF.wav OTHER.wav [OTHER.wav ...]
Prints dB per band for each file and the difference from REF (positive = OTHER is brighter there).
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.voice_match import load  # noqa: E402

BANDS = [(60, 125), (125, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 6000), (6000, 8000), (8000, 11000)]


def ltas(path):
    sr = 24000
    x = load(path, sr)
    n = 2048
    frames = [x[i:i + n] for i in range(0, len(x) - n, n // 2)]
    rms = np.array([np.sqrt(np.mean(f**2)) for f in frames])
    keep = rms > np.percentile(rms, 95) * 10 ** (-30 / 20)
    spec = np.mean([np.abs(np.fft.rfft(f * np.hanning(n))) ** 2 for f, k in zip(frames, keep) if k], axis=0)
    freqs = np.fft.rfftfreq(n, 1 / sr)
    band_db = [10 * np.log10(spec[(freqs >= lo) & (freqs < hi)].mean()) for lo, hi in BANDS]
    ref = band_db[3]
    return [round(b - ref, 1) for b in band_db]


if __name__ == "__main__":
    base = ltas(sys.argv[1])
    print("band Hz      ", " ".join(f"{lo}-{hi}".rjust(10) for lo, hi in BANDS))
    print(Path(sys.argv[1]).name[:12].ljust(13), " ".join(f"{v:10.1f}" for v in base))
    for p in sys.argv[2:]:
        v = ltas(p)
        print(Path(p).name[:12].ljust(13), " ".join(f"{a - b:+10.1f}" for a, b in zip(v, base)), "(diff)")


def match_curve(ref_path, other_paths, strength=0.85, lo=-6.0, hi=8.0):
    """EQ points that move OTHER's average spectrum toward REF's (anchored at 500-1000 Hz)."""
    base = ltas(ref_path)
    diffs = np.mean([np.array(ltas(p)) - np.array(base) for p in other_paths], axis=0)
    points = []
    for (b_lo, b_hi), d in zip(BANDS, diffs):
        centre = float(np.sqrt(b_lo * b_hi))
        points.append([round(centre), round(float(np.clip(-d * strength, lo, hi)), 2)])
    return points
