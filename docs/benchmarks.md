# Benchmarks

> **Historical.** Measured during model selection. For the chosen setup (Qwen3-TTS 1.7B with
> QA) the production speed is about 0.85× real time; see [final-candidates.md](final-candidates.md).

Machine: Apple M5 (10-core GPU), 32 GB, macOS 27.0.1, mlx 0.32.4, mlx-audio 0.6.1.
Test: `scripts/bench.py` on six paragraphs (~300 words, ~1.5 minutes of speech), one
paragraph per generation call, model default voice, fixed seed. Run on 2026-10-21.

Background load during the tests: a Colima (Docker) VM, a browser and editors were open,
and the system already had 13–15 GB in swap before any test started. Closing those
gives more headroom.

| Model | RTF | 10 h book | MLX peak | Swap-outs during run | Lowest free memory | Errors |
|---|---:|---:|---:|---:|---:|---|
| MOSS 8B v1.5, 8-bit | 1.25 | ~12.5 h | 17.5 GB | 82k pages (1.3 GB) | 18% | none |
| MOSS Local-Transformer v1.5, 8-bit | 0.90 | ~9 h | 14.5 GB | 146k pages (2.3 GB) | 23% | none |
| Qwen3-TTS 1.7B Base, bf16 | 0.78 | ~7.8 h | 9.2 GB | 0 | 35% | none |
| MOSS 8B v1.5, bf16 (one-time test) | 3.33 | ~33 h | 25.4 GB | 3.1M pages (~50 GB) | 8% | none, but heavy swapping |

RTF = generation time ÷ audio length; below 1.0 is faster than real time.
"10 h book" is generation time only; QA transcription and retries add roughly 10–15%.

## Word error rate on the benchmark text (Whisper large-v3-turbo)

| Model | WER | Main misses |
|---|---:|---|
| MOSS 8B 8-bit | 2.7% | unusual surname, "evenings" → "evening" |
| MOSS Local 8-bit | 3.7% | unusual surname, "ton" → "tonne", "logbook" split |
| Qwen3 1.7B | 2.0% | unusual surname, "watched" → "washed" |

All three struggle with the made-up surname "Okonkwo-Lindqvist", which is what
`pronunciations.yaml` is for.

## Verdict on bf16 MOSS 8B

Rejected. It peaked at 25.4 GB of MLX memory (the GPU working-set limit is 26.8 GB),
pushed about 50 GB of pages through swap, dropped free memory to 8%, and got slower
as it went (the last paragraph took 6× real time). The 8-bit version is the right
choice for this machine.
