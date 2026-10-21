# Scripts

You only need `download_models.py`. Everything else is the research toolkit that produced
the results in `docs/`; it is kept so the tests can be repeated (for example after an
mlx-audio upgrade). Run them from the repo root with `uv run python scripts/<name>.py`.

| Script | Purpose | Results |
|---|---|---|
| `download_models.py` | Fetch model weights into the Hugging Face cache (`core`, `fast`, `moss`, `bf16`) | |
| `bench.py` | Speed, memory and swap for one model on ~1.5 min of narration | `docs/benchmarks.md` |
| `ab_test.py` | First listening test across MOSS-TTS and Qwen3-TTS | `docs/ab-test.md` |
| `wer_check.py` | Word error rate of benchmark WAVs | |
| `qwen_tune.py` | Qwen3 variables one at a time (normalization, temperature, chunking, presets) | `docs/qwen3-tuning.md` |
| `design_voices.py` | Create narrator voices from text descriptions (Qwen3 VoiceDesign) | `voices/` |
| `finals.py` | The 8 production-pipeline candidates | `docs/final-candidates.md` |
| `chunk_length_test.py` | Reliability vs chunk size on real book text | `docs/chunk-length.md` |

Audio from these goes to `ab_test/` (git-ignored). `bench.py` and `ab_test.py` need the
MOSS models (`download_models.py moss`), which the main workflow no longer uses.
