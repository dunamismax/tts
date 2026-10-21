# Environment setup (technical)

Everything runs from a project-local Python 3.12 environment managed by
[uv](https://docs.astral.sh/uv/). Nothing touches the system Python.

## Prerequisites (already present on this Mac)

- uv 0.10.7 (`~/.local/bin/uv`)
- Homebrew and ffmpeg 9.0.2 (`/opt/homebrew/bin/ffmpeg`)
- git, with `origin` pushing to GitHub and Codeberg

## Rebuild exactly

```bash
cd ~/AudiobookTTS          # symlink to ~/github/tts
uv sync --locked           # installs the exact versions in uv.lock
uv run python scripts/download_models.py core
```

`core` downloads about 36 GB into `~/.cache/huggingface/hub`. `optional` adds the Qwen3
CustomVoice and VoiceDesign models (9 GB). `bf16` adds full-precision MOSS 8B (17 GB,
not recommended).

## Pinned direct dependencies

| Package | Version | Why |
|---|---|---|
| mlx-audio | 0.6.1 | TTS and STT models on MLX (pulls mlx 0.32.4, transformers 5.20.2) |
| ebooklib | 0.20 | EPUB reading |
| beautifulsoup4 | 4.15.0 | HTML to text for EPUB chapters |
| pymupdf | 2.0 | PDF text extraction (AGPL license, fine for personal use) |
| jiwer | 4.0.0 | Word error rate |
| num2words | 0.5.14 | Number expansion |
| pyyaml | 6.0.3 | Config files |
| soundfile | 0.14.0 | WAV I/O |

All transitive versions are locked in `uv.lock`.

## Folder layout

`~/AudiobookTTS` → `~/github/tts` (symlink). Large working data stays in git-ignored
folders inside it: `voices/`, `projects/`, `books/`, `ab_test/`, `logs/`, `.venv/`.
