"""Benchmark one TTS model on about two minutes of narration.

Usage: uv run python scripts/bench.py MODEL [--out DIR] [--ref-audio WAV --ref-text TEXT]

Records load time, generation time, real-time factor, MLX peak memory, process peak
RSS, swap-outs during the run and the lowest system free-memory percentage seen.
Writes a WAV and a JSON result to --out.
"""

from __future__ import annotations

import argparse
import json
import re
import resource
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import mlx.core as mx  # noqa: E402
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

from abtts.engines import Engine, Voice  # noqa: E402

BENCH_PARAGRAPHS = [
    "The lighthouse stood at the end of a long spit of grey stone, and for most of the year "
    "nobody but the keeper and the gulls paid it any attention. It had been built in the "
    "spring of eighteen seventy-two, by a company that went bankrupt before the lamp was lit.",
    "Margaret Okonkwo-Lindqvist arrived on a Tuesday in late October, carrying two suitcases, "
    "a crate of books, and a letter from the harbour board that promised her a salary of "
    "forty pounds a year, a ton of coal, and as much fish as she cared to catch.",
    "\"You'll not last the winter,\" said the boatman, as he set her bags down on the jetty. "
    "\"Nobody does.\" She thanked him, paid him a shilling more than he had asked, and watched "
    "his little boat until it disappeared into the mist.",
    "The first weeks were quiet. She learned the rhythm of the lamp, the clockwork that turned "
    "the great lens, and the particular groan the stairs made in a north-easterly gale. In the "
    "evenings she read by the stove, and in the mornings she wrote long letters to her sister "
    "in Edinburgh, letters that would wait a fortnight for the supply boat.",
    "It was on the ninth of December, a little after three in the morning, that she first "
    "saw the second light. It burned low on the water, perhaps a mile to the south, steady and "
    "white, exactly where the charts insisted there was nothing at all but open sea.",
    "She watched it for an hour. Then she lit a candle, opened the logbook, and wrote, in a "
    "hand that did not shake nearly as much as she expected: Light observed, bearing south by "
    "south-west, origin unknown. Keeper remains at her post.",
]


class MemoryWatch(threading.Thread):
    """Samples system free-memory percentage once a second."""

    def __init__(self):
        super().__init__(daemon=True)
        self.min_free = 100
        self.stop = threading.Event()

    def run(self):
        while not self.stop.is_set():
            pct = free_memory_percent()
            if pct is not None:
                self.min_free = min(self.min_free, pct)
            self.stop.wait(1.0)


def free_memory_percent() -> int | None:
    out = subprocess.run(["memory_pressure", "-Q"], capture_output=True, text=True).stdout
    m = re.search(r"free percentage:\s*(\d+)%", out)
    return int(m.group(1)) if m else None


def swapouts() -> int:
    out = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
    m = re.search(r"Swapouts:\s+(\d+)", out)
    return int(m.group(1)) if m else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--out", default=str(ROOT / "ab_test" / "bench"))
    ap.add_argument("--ref-audio")
    ap.add_argument("--ref-text")
    ap.add_argument("--seed", type=int, default=1234)
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = Engine(args.model, voice=Voice(ref_audio=args.ref_audio, ref_text=args.ref_text))

    watch = MemoryWatch()
    watch.start()
    swap_before = swapouts()
    errors = []

    t0 = time.perf_counter()
    engine.load()
    sr = engine.sample_rate
    load_s = time.perf_counter() - t0

    pieces, gen_s, chunk_stats = [], 0.0, []
    for i, para in enumerate(BENCH_PARAGRAPHS):
        t = time.perf_counter()
        try:
            audio, sr = engine.synth(para, seed=args.seed)
        except Exception as exc:  # recorded in the report, the run continues
            errors.append(f"chunk {i}: {type(exc).__name__}: {exc}")
            continue
        dt = time.perf_counter() - t
        gen_s += dt
        pieces.append(audio)
        pieces.append(np.zeros(int(0.7 * sr), dtype=np.float32))
        chunk_stats.append({"chunk": i, "seconds_audio": len(audio) / sr, "seconds_gen": dt})
        print(f"chunk {i}: {len(audio) / sr:.1f}s audio in {dt:.1f}s", flush=True)

    watch.stop.set()
    watch.join()
    swap_delta = swapouts() - swap_before

    audio = np.concatenate(pieces) if pieces else np.zeros(1, dtype=np.float32)
    audio_s = sum(c["seconds_audio"] for c in chunk_stats)
    name = args.model if not args.ref_audio else f"{args.model}_clone"
    wav = out_dir / f"{name}.wav"
    sf.write(wav, audio, sr)

    result = {
        "model": args.model,
        "repo": engine.repo,
        "sample_rate": sr,
        "load_seconds": round(load_s, 1),
        "audio_seconds": round(audio_s, 1),
        "generation_seconds": round(gen_s, 1),
        "rtf": round(gen_s / audio_s, 3) if audio_s else None,
        "mlx_peak_memory_gb": round(mx.get_peak_memory() / 1e9, 2),
        "process_peak_rss_gb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9, 2),
        "swapouts_during_run": swap_delta,
        "min_system_free_memory_pct": watch.min_free,
        "errors": errors,
        "chunks": chunk_stats,
        "wav": str(wav),
    }
    (out_dir / f"{name}.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "chunks"}, indent=2))


if __name__ == "__main__":
    main()
