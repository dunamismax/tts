"""Find the chunk length Qwen3-TTS handles most reliably, using real book text.

Usage: uv run python scripts/chunk_length_test.py BOOK [--chars 3600] [--sizes 300,500,800,1200]

Takes the first ~N characters of the book's first chapter, packs whole sentences into
chunks of at most each size, renders them with the configured voice and settings (no
retries), and reports WER, pace spread and speed per size. Results: ab_test/chunk_length/.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import soundfile as sf  # noqa: E402

from abtts.books import read_book  # noqa: E402
from abtts.chunking import split_sentences  # noqa: E402
from abtts.engines import Engine  # noqa: E402
from abtts.project import load_pronunciations, load_settings, voice_spec  # noqa: E402
from abtts.qa import Transcriber, word_error_rate  # noqa: E402
from abtts.render import trim_edges  # noqa: E402
from abtts.textnorm import normalize_for_tts  # noqa: E402

OUT = ROOT / "ab_test" / "chunk_length"


def pack(sentences: list[str], size: int) -> list[str]:
    chunks, cur = [], ""
    for s in sentences:
        if cur and len(cur) + 1 + len(s) > size:
            chunks.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    return chunks + ([cur] if cur else [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("book")
    ap.add_argument("--chars", type=int, default=3600)
    ap.add_argument("--sizes", default="300,500,800,1200")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    settings = load_settings()
    pron = load_pronunciations()
    book = read_book(Path(args.book))
    sentences, total = [], 0
    for para in book.chapters[0]["paragraphs"]:
        for s in split_sentences(normalize_for_tts(para, pronunciations=pron)):
            sentences.append(s)
            total += len(s)
        if total >= args.chars:
            break

    voice, _ = voice_spec(settings)
    engine = Engine(settings["model"], voice=voice, sampling=dict(settings["sampling"]))
    engine.load()
    runs = {}
    for size in [int(x) for x in args.sizes.split(",")]:
        chunks = pack(sentences, size)
        rows = []
        for i, text in enumerate(chunks):
            t = time.perf_counter()
            audio, sr = engine.synth(text, seed=settings["seed"])
            audio = trim_edges(audio, sr)
            gen = time.perf_counter() - t
            wav = OUT / f"size{size}_{i:02d}.wav"
            sf.write(wav, audio, sr)
            rows.append({"text": text, "wav": str(wav), "seconds": len(audio) / sr, "gen": gen})
        runs[size] = rows
        print(f"size {size}: {len(chunks)} chunks rendered", flush=True)
    engine.unload()

    stt = Transcriber()
    summary = []
    for size, rows in runs.items():
        for r in rows:
            r["transcript"] = stt.transcribe(r["wav"])
            r["wer"] = word_error_rate(r["text"], r["transcript"])
            r["cps"] = len(r["text"]) / r["seconds"]
        cps = [r["cps"] for r in rows]
        words = sum(len(r["text"].split()) for r in rows)
        weighted_wer = sum(r["wer"] * len(r["text"].split()) for r in rows) / words
        summary.append({
            "size": size, "chunks": len(rows),
            "avg_chars": round(statistics.mean(len(r["text"]) for r in rows)),
            "wer": weighted_wer, "worst_chunk_wer": max(r["wer"] for r in rows),
            "over_8pct": sum(r["wer"] > 0.08 for r in rows),
            "pace_spread": statistics.pstdev(cps) / statistics.mean(cps),
            "rtf": sum(r["gen"] for r in rows) / sum(r["seconds"] for r in rows),
        })
    (OUT / "results.json").write_text(json.dumps({"summary": summary, "runs": runs}, indent=2))
    lines = ["| Max chars | Chunks | Avg chars | WER | Worst chunk | Chunks > 8% | Pace spread | RTF |",
             "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for s in summary:
        lines.append(f"| {s['size']} | {s['chunks']} | {s['avg_chars']} | {s['wer']:.1%} | {s['worst_chunk_wer']:.1%} | "
                     f"{s['over_8pct']} | {s['pace_spread']:.1%} | {s['rtf']:.2f} |")
    (OUT / "RESULTS.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
