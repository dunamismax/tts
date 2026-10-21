# Documentation

Start with [how-it-works.md](how-it-works.md). The rest is the record of how the current
setup was chosen, in the order it happened.

| Document | What's in it |
|---|---|
| [how-it-works.md](how-it-works.md) | The pipeline (import, normalization, chunking, QA, caching, mastering, export) and the web studio |
| [setup.md](setup.md) | Rebuilding the environment, pinned versions, model downloads |
| [model-research.md](model-research.md) | First round: MOSS-TTS v1.5 (8B and Local) vs Qwen3-TTS, API facts from the mlx-audio source and model cards |
| [benchmarks.md](benchmarks.md) | Speed, memory and swap per model on this Mac, including the rejected bf16 MOSS 8B |
| [ab-test.md](ab-test.md) | The first listening test (17 files, 3 model families) |
| [qwen3-tuning.md](qwen3-tuning.md) | After the user picked Qwen3: normalization, temperature, chunk size, presets, pronunciation |
| [final-candidates.md](final-candidates.md) | The 8 production-pipeline candidates; **F1 was chosen** |
| [chunk-length.md](chunk-length.md) | Why chunks are at most 500 characters |
| [voice-matching.md](voice-matching.md) | Making British Male's narration match its demo clip (tempo, pitch, pauses, tone) |

## Decisions at a glance

| Decision | Choice | Why |
|---|---|---|
| Model | Qwen3-TTS-12Hz-1.7B-Base, bf16 (mlx-community) | Sounded clearly better than MOSS-TTS v1.5 to the user; largest Qwen3-TTS |
| Voice | `britishmale` reference clip, cloned | User's pick: refined British (RP) male, smooth and mellow (replaced `designmale`, the F1 voice) |
| Temperature | 0.9 (model card default) | User's pick (F1); kept with the new voice |
| Delivery | British Male: tempo 0.88, pitch −0.5 st, pauses ×1.15, tone EQ | Matches the demo clip's pace and tone (voice-matching.md) |
| Text | Numbers, dates, money, abbreviations spelled out | Fixes preset voices, harmless for clones |
| Chunks | Paragraphs, at most 500 characters, never mid-sentence | See chunk-length.md |
| QA | Whisper large-v3-turbo, WER > 8% or abnormal pace → up to 3 retries | Catches skips, repeats, garbles |
| Mastering | RMS −20 dB, peaks ≤ −3.5 dB, −70 dB room tone, 44.1 kHz mono | ACX specs with margin |
| Interface | Local web studio (FastAPI + plain JS) over the CLI engine | No Terminal needed; offline; one narration at a time |
| Rejected | MOSS-TTS 8B bf16 | 25 GB peak, heavy swapping, RTF 3.3 |
