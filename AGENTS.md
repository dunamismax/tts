# AGENTS.md

Guidance for anyone (human or automated) working in this repository.

## What this repo is

A local, offline audiobook narration workflow for an Apple Silicon Mac (M5, 32 GB),
built on [mlx-audio](https://github.com/Blaizzy/mlx-audio). `~/AudiobookTTS` is a
symlink to this repo, so both paths refer to the same folder.

## Layout

- `audiobook.py`: the command-line tool (once built)
- `abtts/`: library code (engines, text cleanup, QA, mastering)
- `scripts/`: setup, benchmark and A/B test helpers
- `docs/`: research notes, benchmark results, decisions
- `config.yaml`, `pronunciations.yaml`: user-editable settings
- Git-ignored working data: `ab_test/`, `projects/`, `books/`, `voices/`, `output/`, `logs/`, `.venv/`

## Rules

1. **Commit messages must never mention AI, assistants, Claude, or any tool attribution.**
   No `Co-Authored-By` trailers or "generated with" lines. Write plain, imperative
   messages ("Add chapter splitter for EPUB").
2. **Push to both remotes.** `origin` fetches from GitHub and pushes to GitHub and
   Codeberg (`git push` updates both). Check with `git remote -v`. Never force-push `main`.
3. **Never delete or overwrite the user's files.** Write new outputs to new files.
   Audio, books, voices and projects stay out of git.
4. **Pin every dependency.** Use `uv add pkg==X.Y.Z`; commit `pyproject.toml` and `uv.lock`.
   Python 3.12 via uv only. No system Python, no `sudo`. Ask before installing anything system-wide.
5. **Do not guess APIs.** Read the installed mlx-audio source
   (`.venv/lib/python3.12/site-packages/mlx_audio/tts/models/...`) and the model cards
   before changing generation code. Record what you learn in `docs/`.
6. **Model choice.** The workflow uses Qwen3-TTS 1.7B (bf16) only; the user chose it by ear
   over MOSS-TTS (see `docs/qwen3-tuning.md`). Don't reintroduce MOSS without asking.
   The Mac has 32 GB; MLX's working-set limit is about 26.8 GB.
7. **Pronunciations** are plain-English respellings with CAPITALIZED stress
   (`pronunciations.yaml`); Qwen3 does not read IPA.
8. **Only clone voices the user owns or has permission to use.**
9. Keep `README.md` written for a non-programmer. Put technical detail in `docs/`.

## Common commands

```bash
uv sync --locked                                  # rebuild the environment exactly
uv run python scripts/download_models.py core     # fetch model weights
uv run python scripts/finals.py render F3         # render one voice candidate
uv run python scripts/finals.py report            # rebuild the candidates table
```
