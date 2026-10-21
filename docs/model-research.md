# Model research notes

Verified on 2026-10-21 against mlx-audio **0.6.1** (released 2026-10-20) source and the
Hugging Face model cards. Re-check these when upgrading mlx-audio.

## Machine

- MacBook Pro (Mac17,2), Apple M5: 10-core CPU (4 performance + 6 efficiency), 10-core GPU
- 32 GB unified memory; `mx.device_info()` reports a recommended working set of 26.8 GB
- macOS 27.0.1

## Candidates

| Key | Repo | Type | Output | Weights on disk |
|---|---|---|---|---|
| `moss8b` | `luisarn/MOSS-TTS-v1.5-MLX-8bit` | MOSS-TTS v1.5 8B delay-pattern, 8-bit affine (gs 64) | 24 kHz mono | 9.2 GB + 7.1 GB audio tokenizer |
| `mosslocal` | `mlx-community/MOSS-TTS-Local-Transformer-v1.5-8bit` | MOSS Local-Transformer v1.5, 8-bit | 48 kHz stereo | 4.9 GB + 8.5 GB tokenizer v2 |
| `qwen3` | `mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16` | Qwen3-TTS 1.7B Base | 24 kHz mono | 4.5 GB |
| `qwen3-custom` | `mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16` | preset speakers | 24 kHz mono | 4.5 GB |
| `qwen3-design` | `mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16` | voice from text description | 24 kHz mono | 4.5 GB |
| `moss8b-bf16` | `OpenMOSS-Team/MOSS-TTS-v1.5` | full precision (tested once, rejected) | 24 kHz mono | 17.0 GB |

The Local-Transformer v1.5 has an official mlx-community 8-bit conversion, so that one is used.
mlx-community has no quantized MOSS 8B v1.5; the luisarn conversion fills that gap.

Speech-to-text for QA: `mlx-community/whisper-large-v3-turbo-asr-fp16` (1.6 GB), via `mlx_audio.stt`.

## MOSS-TTS v1.5 facts (from the model cards and `mlx_audio/tts/models/moss_tts/`)

- `model.generate(text=..., ref_audio=..., language="English", max_tokens=..., audio_temperature=...,
  audio_top_p=..., audio_top_k=..., audio_repetition_penalty=...)`.
- **Language tag**: v1.5 is stronger on almost every language when `language` is set. We always pass `"English"`.
- **Voice cloning** needs only reference audio in the default "generation" mode. `ref_text` is used only
  in "continuation" mode.
- **Pauses**: inline `[pause 3.2s]` markers are passed through to the prompt.
- **IPA**: wrap IPA in slashes, `/həloʊ/`. It can be mixed with ordinary text in the same sentence.
- **Duration**: 1 s ≈ 12.5 audio tokens. `max_tokens` caps generation; we derive it from text length
  so a runaway chunk cannot go on forever.
- **Recommended sampling** (both v1.5 cards): audio temperature 1.7, top-p 0.8, top-k 25, repetition
  penalty 1.0. "Lower values stabilize prosody." The 1.0 card lists 1.0 / 0.95 / 50 / 1.1 for the Local model.
- mlx-audio normalizes text before prompting (`text.py`): newlines become `。`, `...` becomes `。`,
  and `--`/`——` runs become `。`. Our cleanup produces single-line chunks with real punctuation
  so these rules don't change the meaning.
- The Local v1.5 codec is stereo; we down-mix to mono, since ACX wants mono anyway.
- Streaming is implemented only for Local v1.5 (not needed for book rendering).

## Qwen3-TTS facts (`mlx_audio/tts/models/qwen3_tts/`)

- Base models have **no preset speakers**. Clone with `ref_audio` + `ref_text` (ICL mode). In ICL
  mode mlx-audio raises the repetition penalty to at least 1.5 automatically.
- CustomVoice English speakers: Ryan, Aiden (others exist but are tuned for Chinese).
- VoiceDesign takes `instruct="description of the voice"`.
- `generation_config.json` defaults: temperature 0.9, top-k 50, top-p 1.0, repetition penalty 1.05.
- `lang_code="english"`.
- Text is split on `split_pattern` (default newline); our chunks have no newlines.

## Seeds and consistency

`mx.random.seed(seed)` before each chunk makes output reproducible (verified: identical durations
across reruns). Voice consistency across a whole book comes from cloning one fixed reference clip
for every chunk. Without a reference, MOSS picks a voice from the text and seed, so nothing anchors
it between chunks. Use a reference clip for books.
