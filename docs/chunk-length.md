# Chunk length

Tested 2026-10-21 with `scripts/chunk_length_test.py` on the opening ~3,600 characters of
*The Happy Prince* (Project Gutenberg #902), F1 settings (designmale, temperature 0.9), no
retries. Whole sentences were packed into chunks of at most N characters, crossing paragraph
boundaries so the long sizes really were long.

| Max chars | Chunks | Avg chars | WER | Worst chunk | Chunks > 8% | Pace spread | RTF |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 300 | 16 | 229 | 1.6% | 4.3% | 0 | 7.2% | 0.89 |
| 500 | 9 | 407 | 1.3% | 3.5% | 0 | 10.0% | 0.82 |
| 800 | 5 | 734 | 1.3% | 2.2% | 0 | 6.0% | 0.89 |
| 1200 | 4 | 918 | 1.3% | 3.9% | 0 | 6.9% | 0.90 |

WER is weighted by words. Pace spread is the standard deviation of characters per second
across chunks, divided by the mean (lower = more even delivery).

## Result

Every size was reliable: no chunk above the 8% retry threshold, about 1.3% WER overall
(mostly "Swallow"/"swallow" capitalization and comma-level differences). Longer chunks did
not improve accuracy or evenness, and they make each QA retry more expensive and pauses
coarser. **500 characters** had the best speed (RTF 0.82) with no accuracy cost, so it is
the default (`chunking.max_chars` in `config.yaml`). A single sentence longer than the limit
is still sent whole, which this test shows is safe up to at least ~900 characters.
