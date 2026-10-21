# Final voice candidates

Rendered 2026-10-21 by `scripts/finals.py` through the full production pipeline. Audio is in
`~/AudiobookTTS/ab_test/finals/` (MP3 for listening, mastered WAV alongside; not in git).

Same text for every candidate: a spoken chapter title ("Chapter One. Carrow Junction."),
then the 2-minute test passage (dialogue, a 90-word sentence, dates, times, money, an unusual name).

Pipeline: text normalization + `pronunciations.yaml` → paragraph chunks (≤500 chars, never
mid-sentence) → Qwen3-TTS 1.7B bf16 → Whisper QA (retry up to 3× if WER > 8% or pace
abnormal) → edge-trim, 1.75 s after the title, 0.7 s between paragraphs → ACX mastering
(44.1 kHz mono, RMS −20 dB, peaks ≤ −3.5 dB, −72 dB pink-noise room tone, 0.75 s head /
2 s tail) → MP3 192 kbps CBR.

| # | File | Voice | Temperature |
|---|---|---|---:|
| F1 | F1_designmale_t0.9.mp3 | Your 3a voice (designmale clone) | 0.9 |
| F2 | F2_designmale_t0.7.mp3 | Your 3b voice (designmale clone) | 0.7 |
| F3 | F3_designmale_t0.8.mp3 | Same voice, in-between setting (lowest error rate in tuning) | 0.8 |
| F4 | F4_deepbaritone_t0.8.mp3 | New: deep, warm American baritone, sixties | 0.8 |
| F5 | F5_britishmale_t0.8.mp3 | New: refined British (RP) male, fifties | 0.8 |
| F6 | F6_warmfemale_t0.8.mp3 | New: warm, mature American female, forties | 0.8 |
| F7 | F7_preset-Ryan_narration.mp3 | Qwen3 built-in speaker Ryan + narration instruction | 0.9 |
| F8 | F8_preset-Aiden_narration.mp3 | Qwen3 built-in speaker Aiden + narration instruction | 0.9 |

All eight pass ACX: RMS −20.1 to −20.3 dB, peaks −3.5 dB, noise floor −71.6 to −72.5 dB
(MP3s: RMS ≈ −20.5 dB, peaks −3.7 to −3.8 dB).

## Speed

Measured with QA on F3 after fixing two QA scoring bugs (below): **RTF 0.85**, so a 10-hour
book takes about 8.5 hours. Cloned voices (F1–F6) run at RTF ≈ 0.85–1.0, the built-in
speakers (F7–F8) at ≈ 0.75. Overnight is enough for a typical book.

## QA scoring bugs found and fixed during this run

The first finals run retried the name-heavy paragraph 3 times for every voice. The audio
was fine; the scorer wasn't:
- "the fourteenth of March" (text sent) vs Whisper's "the 14th of March" counted as 3 errors.
  Spelled-out dates are now normalized like digit dates.
- "two hundred fifty" vs "two hundred and fifty" counted as an error. "and" after
  hundred/thousand is now ignored.
- One misheard word in a 4-word chapter title is 25% WER. Short chunks may now have one.
