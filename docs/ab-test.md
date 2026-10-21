# A/B listening test (Step 4)

> **Historical.** The user preferred Qwen3-TTS (files 3a and 3b), which led to
> [qwen3-tuning.md](qwen3-tuning.md).

Rendered 2026-10-21 with `scripts/ab_test.py`. Audio is in `~/AudiobookTTS/ab_test/` (not in git).
The passage (305 words, ~2 minutes) has dialogue with curly quotes, a 90-word sentence,
a date ("Tuesday, the 14th of March 1923"), times ("7:45", "11:58 p.m."), currency ("£250"),
a decimal, an ordinal, abbreviations ("Mr.", "p.m.") and an unusual name ("Aoife Szczepańska").
The text was given to the models raw, exactly as a book would print it.

Voices: no personal clip yet, so two narrator voices were created with Qwen3 VoiceDesign
(`designmale`, `designfemale`), saved as 14–17 s reference clips, and cloned by every model.
`default` = MOSS with no reference. `preset:Ryan/Aiden` = Qwen3 CustomVoice speakers.
`design:…` = Qwen3 VoiceDesign narrating directly from the description.

## Observations

- **Names**: Whisper heard "Aoife" as "Ifa"/"Iva", which matches the real Irish pronunciation
  (EE-fa), so most models got the first name right. The Polish surname varies by model and
  run. That is what `pronunciations.yaml` is for.
- **Numbers, dates, times, currency, abbreviations**: every cloned-voice configuration (MOSS 8B,
  MOSS Local, Qwen3 Base) read them all correctly from raw text. The Qwen3 preset and
  voice-design models did not: "1919" became "one hundred and ninety-nine" or "one thousand nine
  hundred and nineteen", and "£250" was garbled. Number expansion is only essential for those.
- **RTF of file 1a** (2.17) includes one-time warm-up; MOSS 8B's steady-state RTF is 1.2–1.4.
- **File 2b** ends with a phantom "thank you" in the transcript, a Whisper hallucination on
  trailing silence or a stray model artifact. Worth a listen.
- Lower temperature ("steady") did not reduce errors for MOSS 8B and made it slightly slower.
  For Qwen3 it lowered WER a little.

## Results table

| File | Model | Voice | Settings | RTF | 10 h book | WER | MLX peak |
|---|---|---|---|---:|---:|---:|---:|
| 1a_moss8b_designmale_card.wav | moss8b | designmale | card (temperature=1.7, top_p=0.8, top_k=25, repetition_penalty=1.0) | 2.17 | 21.7 h | 0.6% | 17.73 GB |
| 1b_moss8b_designmale_steady.wav | moss8b | designmale | steady (temperature=1.3, top_p=0.8, top_k=25, repetition_penalty=1.0) | 1.38 | 13.8 h | 0.6% | 17.78 GB |
| 1c_moss8b_designfemale_card.wav | moss8b | designfemale | card (temperature=1.7, top_p=0.8, top_k=25, repetition_penalty=1.0) | 1.20 | 12.0 h | 0.3% | 17.63 GB |
| 1d_moss8b_designfemale_steady.wav | moss8b | designfemale | steady (temperature=1.3, top_p=0.8, top_k=25, repetition_penalty=1.0) | 1.37 | 13.7 h | 0.6% | 17.63 GB |
| 1e_moss8b_default_card.wav | moss8b | default | card (temperature=1.7, top_p=0.8, top_k=25, repetition_penalty=1.0) | 1.25 | 12.5 h | 0.9% | 17.56 GB |
| 2a_mosslocal_designmale_card.wav | mosslocal | designmale | card (temperature=1.7, top_p=0.8, top_k=25, repetition_penalty=1.0) | 1.07 | 10.7 h | 0.6% | 15.99 GB |
| 2b_mosslocal_designmale_v10local.wav | mosslocal | designmale | v10local (temperature=1.0, top_p=0.95, top_k=50, repetition_penalty=1.1) | 0.98 | 9.8 h | 1.2% | 15.2 GB |
| 2c_mosslocal_designfemale_card.wav | mosslocal | designfemale | card (temperature=1.7, top_p=0.8, top_k=25, repetition_penalty=1.0) | 0.97 | 9.7 h | 0.6% | 15.73 GB |
| 2d_mosslocal_designfemale_v10local.wav | mosslocal | designfemale | v10local (temperature=1.0, top_p=0.95, top_k=50, repetition_penalty=1.1) | 1.06 | 10.6 h | 0.9% | 15.39 GB |
| 3a_qwen3_designmale_card.wav | qwen3 | designmale | card (temperature=0.9, top_k=50, top_p=1.0, repetition_penalty=1.05) | 0.89 | 8.9 h | 0.9% | 11.19 GB |
| 3b_qwen3_designmale_steady.wav | qwen3 | designmale | steady (temperature=0.7, top_k=50, top_p=1.0, repetition_penalty=1.05) | 0.88 | 8.8 h | 0.6% | 11.06 GB |
| 3c_qwen3_designfemale_card.wav | qwen3 | designfemale | card (temperature=0.9, top_k=50, top_p=1.0, repetition_penalty=1.05) | 0.90 | 8.9 h | 0.6% | 10.66 GB |
| 3d_qwen3_designfemale_steady.wav | qwen3 | designfemale | steady (temperature=0.7, top_k=50, top_p=1.0, repetition_penalty=1.05) | 0.89 | 8.9 h | 0.6% | 10.53 GB |
| 4a_qwen3-custom_Ryan_card.wav | qwen3-custom | preset:Ryan | card (temperature=0.9, top_k=50, top_p=1.0, repetition_penalty=1.05) | 0.76 | 7.5 h | 3.7% | 9.64 GB |
| 4b_qwen3-custom_Aiden_card.wav | qwen3-custom | preset:Aiden | card (temperature=0.9, top_k=50, top_p=1.0, repetition_penalty=1.05) | 0.73 | 7.3 h | 3.1% | 9.64 GB |
| 5a_qwen3-design_vd-designmale_card.wav | qwen3-design | design:designmale | card (temperature=0.9, top_k=50, top_p=1.0, repetition_penalty=1.05) | 0.72 | 7.2 h | 1.2% | 9.41 GB |
| 5b_qwen3-design_vd-designfemale_card.wav | qwen3-design | design:designfemale | card (temperature=0.9, top_k=50, top_p=1.0, repetition_penalty=1.05) | 0.75 | 7.5 h | 1.2% | 10.13 GB |

