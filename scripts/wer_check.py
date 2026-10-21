"""Transcribe WAV files and print word error rate against the benchmark text.

Usage: uv run python scripts/wer_check.py WAV [WAV ...]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from abtts.qa import Transcriber, normalize_for_wer, word_error_rate  # noqa: E402
from scripts.bench import BENCH_PARAGRAPHS  # noqa: E402

if __name__ == "__main__":
    reference = " ".join(BENCH_PARAGRAPHS)
    stt = Transcriber()
    for wav in sys.argv[1:]:
        text = stt.transcribe(wav)
        print(f"{Path(wav).name}: WER {word_error_rate(reference, text):.1%}")
        if "-v" in sys.argv[0:1] or len(sys.argv) == 2:
            print("  REF:", normalize_for_wer(reference))
            print("  HYP:", normalize_for_wer(text))
