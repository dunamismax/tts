# Qwen3-TTS tuning (after the A/B test)

**Decision (2026-10-21):** after listening to the A/B files, Qwen3-TTS sounded clearly
better than every MOSS-TTS option. Favourites: `3a_qwen3_designmale_card` and
`3b_qwen3_designmale_steady`. MOSS is dropped from the workflow; its notes stay in
`model-research.md` and `benchmarks.md` for reference.

There is no larger or newer Qwen TTS model: `Qwen3-TTS-12Hz-1.7B` at bf16 is the top
of the family (checked on Hugging Face, 2026-10-21).

## What was tried (`scripts/qwen_tune.py`)

Same passage, seed and voice as 3a unless noted. Voice similarity is the cosine
similarity of each chunk's Qwen3 speaker embedding to the reference clip (presets: to
their first chunk). It stayed at 0.98 or higher for every variant, so the voice does not
drift between chunks.

| Variant | Chunks | RTF | WER | Voice similarity (min / mean) |
|---|---:|---:|---:|---|
| c1_ryan_norm | 6 | 0.73 | 1.6% | 0.978 / 0.990 |
| c2_ryan_norm_instr | 6 | 0.72 | 0.6% | 0.988 / 0.993 |
| c3_aiden_norm | 6 | 0.72 | 0.6% | 0.992 / 0.996 |
| c4_aiden_norm_instr | 6 | 0.76 | 0.9% | 0.995 / 0.996 |
| t1_raw_t09_para | 6 | 1.03 | 0.9% | 0.992 / 0.994 |
| t2_norm_t09_para | 6 | 1.01 | 0.6% | 0.994 / 0.994 |
| t3_norm_t07_para | 6 | 0.92 | 0.9% | 0.993 / 0.995 |
| t4_norm_t08_para | 6 | 0.87 | 0.3% | 0.994 / 0.995 |
| t5_norm_t09_c250 | 7 | 0.86 | 0.6% | 0.994 / 0.994 |
| t6_norm_t09_whole | 1 | 0.77 | 0.6% | 0.993 / 0.993 |

`t` = temperature, `para` = one chunk per paragraph, `c250` = chunks of at most 250
characters, `whole` = the entire passage as one chunk, `instr` = style instruction
"Calm, warm, measured audiobook narration with natural pauses."

## Findings

- **Text normalization** (numbers, dates, times, currency, abbreviations spelled out)
  fixed the preset speakers: Ryan 4.6% → 0.6% WER (with instruction), Aiden 3.1% → 0.6%.
  It also slightly helps cloned voices, so it is on for everything.
- **Temperature**: 0.8 gave the lowest WER (0.3%) for the favourite voice. 0.7 and 0.9 are
  both fine; the choice is about sound, not accuracy.
- **Chunk size**: paragraphs (up to ~500 characters) work well. A whole 1,900-character
  passage also read correctly but ran together with no paragraph pauses, so the
  workflow keeps paragraph chunks and inserts its own pauses.
- **Pronunciation**: Qwen3 has no IPA syntax. Respelling with capitalized stress works:
  "Eefa Shcheh-PAHN-ska" was heard exactly as intended (Whisper even wrote it back as
  "Aoife"). These go in `pronunciations.yaml`.
- **WER scoring** treats "two hundred fifty" and "two hundred and fifty" as equal, and
  accepts either the respelled or original text, so QA does not retry chunks for nothing.

## Voices

- `designmale`: the 3a/3b voice. Designed with Qwen3 VoiceDesign, saved as a fixed
  17 s reference clip, cloned by Qwen3 Base. Not a built-in preset.
- `deepbaritone`, `britishmale`, `warmfemale`: new voices in the same style, made by
  `scripts/design_voices.py` (3 takes each, best kept, ~25 s references).
- `Ryan`, `Aiden`: Qwen3's only native-English built-in speakers (CustomVoice model).
  The other seven built-ins are Chinese, Japanese or Korean natives.
