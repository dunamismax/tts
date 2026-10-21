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

`core` downloads about 15 GB into `~/.cache/huggingface/hub`: Qwen3-TTS 1.7B Base,
CustomVoice and VoiceDesign (bf16), plus Whisper large-v3-turbo for quality checks.
`moss` and `bf16` fetch the MOSS-TTS models used in the original comparison (not used now).

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
| fastapi | 0.157.0 | Web studio API |
| uvicorn | 0.54.0 | Web studio server |
| python-multipart | 0.0.32 | File uploads in the studio |

All transitive versions are locked in `uv.lock`.

## Folder layout

`~/AudiobookTTS` → `~/github/tts` (symlink, created with `ln -s ~/github/tts ~/AudiobookTTS`).
Working data stays in git-ignored folders inside it: `projects/`, `books/`, `ab_test/`,
`logs/`, `.venv/`. In `voices/`, only the synthetic designed voices are tracked.

## Disk space

Hugging Face cache after the research phase: Qwen3 models + Whisper ≈ 15 GB (needed),
MOSS-TTS models ≈ 38 GB and MOSS bf16 ≈ 17 GB (no longer used). To free the MOSS space:

```bash
uv run hf cache ls
uv run hf cache rm model/luisarn/MOSS-TTS-v1.5-MLX-8bit model/OpenMOSS-Team/MOSS-TTS-v1.5 \
  model/OpenMOSS-Team/MOSS-Audio-Tokenizer model/OpenMOSS-Team/MOSS-Audio-Tokenizer-v2 \
  model/mlx-community/MOSS-TTS-Local-Transformer-v1.5-8bit
```
 Each book project needs roughly 1.5 GB per 10 hours of audio
for the chunk cache, plus its outputs.
