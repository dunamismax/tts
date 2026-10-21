# Matching narration to a voice's demo clip

**Problem (2026-10-21).** The user loved British Male's demo clip (the sample on the Voices
page, `voices/britishmale/ref_24k_mono.wav`) for its tone, speed and pace, but the narration
cloned from it sounded different. The demo was made by Qwen3 VoiceDesign from the description
"…smooth, mellow low-mid voice. Gentle, measured, intimate audiobook delivery." Qwen3 Base
cloning copies the timbre, not that measured pacing.

## Measurements (`scripts/voice_match.py`, `scripts/ltas.py`)

Same 62-word demo transcript, clone at temperatures 0.6–1.0, 3 seeds each:

| | Words/min | Speaking rate | Pause share | Pitch (YIN) |
|---|---:|---:|---:|---:|
| Demo clip | 154 | 197 | 21.5% | 81 Hz |
| Clone, any temperature | 184–190 | 223–227 | 16–18% | 82–89 Hz |

Temperature did not change pace. Tone (average spectrum, speech only, relative to 500–1000 Hz):
the clone was 2–3 dB lighter below 250 Hz and 4–9 dB darker from 2 to 11 kHz.

Narrating directly with VoiceDesign (same description and seed as the demo) was rejected:
on 8 book paragraphs its voice was less like the demo (speaker similarity 0.981 against 0.994
for the clone) and less consistent between paragraphs (0.982 against 0.995), with pitch drifting
up to 111 Hz (`scripts/delivery_test.py`).

## Fix: per-voice delivery settings (`scripts/delivery_fit.py`)

Stored as `delivery:` in `voices/britishmale/voice.yaml` and applied whenever that voice reads:

| Setting | Value | What it does | Where |
|---|---|---|---|
| `temperature` | 0.9 | unchanged, so cached narration stays valid | generation |
| `pause_stretch` | 1.15 | lengthens the narrator's own pauses (≥ 0.12 s) inside each chunk | chapter assembly |
| `pitch` | −0.5 semitones | `asetrate` + `aresample`; also provides part of the slowdown | mastering |
| `tempo` | 0.88 | overall speed; the rest after the pitch step comes from `atempo` (about 9% stretch) | mastering |
| `eq` | +1.4 dB lows, +1.7 to +8 dB above 1.4 kHz | `firequalizer` tone curve fitted on fully processed takes against the demo | mastering |

The pipeline's own pauses (sentence, paragraph, after title) are pre-scaled by the tempo, so
they still come out at the configured lengths. Delivery changes only re-master chapters;
nothing is re-narrated.

## Result (`ab_test/match/`)

| | Words/min | Speaking rate | Pitch | Tone vs demo | WER |
|---|---:|---:|---:|---|---:|
| Demo clip | 154 | 197 | 81 Hz | | 0% |
| New default, *Happy Prince* opening | 157 | 190 | 82 Hz | within ±1.5 dB | 1.1% |
| Old default, *Happy Prince*-style passage (F5) | 169 | 205 | 86 Hz | up to −8.7 dB | |

## Notes

- The first pitch tracker (plain autocorrelation) was accurate on test tones but unreliable on
  speech, and suggested a 1-semitone gap. It was replaced with YIN, validated by measuring audio
  shifted by known amounts (−1 semitone read as −5.9%, the true value is −5.6%). The real gap
  was about half a semitone.
- `firequalizer` with `scale=loglog` silently ignored the dB gains; the code uses `linlog`.
- To fit another voice: `scripts/voice_match.py sweep VOICE` (clone renders of the demo's
  transcript), then `scripts/delivery_fit.py VOICE --write` (add `--tempo/--pause/--pitch` to pin
  values).
