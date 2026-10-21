# AGENTS.md

Guidance for anyone (human or automated) working in this repository.

## What this repo is

A local, offline audiobook narration workflow for an Apple Silicon Mac (M5, 32 GB),
built on [mlx-audio](https://github.com/Blaizzy/mlx-audio) and Qwen3-TTS. `~/AudiobookTTS`
is a symlink to this repo, so both paths refer to the same folder. The owner is not a
programmer and uses it through `README.md`.

## Layout

- `Audiobook Studio.command`: double-click launcher for the web studio (the primary interface)
- `webapp/`: the web studio. `server.py` (FastAPI, job queue) and `static/` (plain HTML/CSS/JS, no build, offline)
- `audiobook.py`: the command-line tool (re-launches itself in `.venv`); the studio runs it as a subprocess
- `abtts/`: library code
  - `books.py` import and cleanup, `textnorm.py` number/abbreviation expansion,
    `chunking.py` sentence-safe chunks, `engines.py` mlx-audio wrappers, `render.py` QA retries,
    `qa.py` Whisper + WER, `audio.py` ffmpeg/ACX mastering, `project.py` cache, assembly, M4B, report,
    `voice.py` reference clip preparation
- `config.yaml`, `pronunciations.yaml`: user settings (keep the inline comments current)
- `voices/`: only the synthetic designed voices are committed; personal clips are git-ignored
- `samples/smoke-test.md`: tiny two-chapter book for end-to-end checks
- `scripts/`: model downloads, plus the research tools that produced `docs/` (benchmarks,
  A/B test, tuning, finals, chunk-length test)
- `docs/`: how it works, setup, and the research record. Read `docs/README.md` first.
- Git-ignored working data: `projects/`, `books/`, `ab_test/`, `logs/`, `.venv/`

## Rules

1. **Commit messages must never mention AI, assistants, Claude, or any tool attribution.**
   No `Co-Authored-By` trailers or "generated with" lines. Write plain, imperative
   messages ("Add chapter splitter for EPUB").
2. **Push to both remotes.** `origin` fetches from GitHub and pushes to GitHub and
   Codeberg (`git push` updates both). Check with `git remote -v`. Never force-push `main`.
3. **Never delete or overwrite the user's files.** Write new outputs to new files. Cached
   takes are never deleted; `redo` makes a new one. Books, audio and projects stay out of git.
4. **Pin every dependency.** Use `uv add pkg==X.Y.Z`; commit `pyproject.toml` and `uv.lock`.
   Python 3.12 via uv only. No system Python, no `sudo`. Ask before installing anything system-wide.
5. **Do not guess APIs.** Read the installed mlx-audio source
   (`.venv/lib/python3.12/site-packages/mlx_audio/tts/models/qwen3_tts/`) and the model cards
   before changing generation code. Record what you learn in `docs/`.
6. **Model choice.** The workflow uses Qwen3-TTS 1.7B Base (bf16) with the `designmale` voice
   at temperature 0.9, chosen by ear by the user (candidate F1, `docs/final-candidates.md`).
   MOSS-TTS was rejected; don't reintroduce it without asking. The Mac has 32 GB; MLX's
   working-set limit is about 26.8 GB.
7. **Pronunciations** are plain-English respellings with CAPITALIZED stress; Qwen3 does not read IPA.
8. **Cache keys.** Anything that changes generated audio must be part of the chunk key in
   `project.build_plan`, or bump `CACHE_VERSION`. Otherwise resumed books mix old and new audio.
9. **Only clone voices the user owns or has permission to use.**
10. Keep `README.md` written for a non-programmer. Put technical detail in `docs/`.
11. **The web studio is the primary interface.** New features go into both the CLI (the engine)
    and the studio. Keep the studio offline (no CDNs or web fonts), bound to 127.0.0.1, with the
    `X-Studio` header check on every non-GET route, and build DOM with `textContent` only.

## Common commands

```bash
uv sync --locked                                     # rebuild the environment exactly
uv run python scripts/download_models.py core        # fetch model weights (~15 GB)
./audiobook.py chapters books/some-book.epub         # check import without creating a project
./audiobook.py preview books/some-book.epub --chapter 1
./audiobook.py make books/some-book.epub
./audiobook.py web                                   # the studio at http://127.0.0.1:8765
```

Quick end-to-end check after code changes: `./audiobook.py make samples/smoke-test.md`
(about 40 seconds of audio, two chapters), then read `projects/the-smoke-test/report.md`.
