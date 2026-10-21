# How it works

Two front ends share one engine (the `abtts/` package): the web studio (`webapp/`) and the
command line (`audiobook.py`). The studio runs every narration as an `audiobook.py` subprocess,
so both behave identically.

```
book file ──► import (books.py) ──► chapters/NN.txt (editable)
                                         │
                       normalize + respell (textnorm.py, pronunciations.yaml)
                                         │
                       chunk at sentence boundaries (chunking.py)
                                         │
             ┌──────── per chunk, skipped if cached (project.py) ────────┐
             │  Qwen3-TTS 1.7B Base, voice clone, fixed seed (engines.py) │
             │  trim edges → Whisper transcript → WER + pace check        │
             │  retry with a new seed up to 3× → keep best (render.py)    │
             └────────────────────────────────────────────────────────────┘
                                         │
             join chunks with fixed pauses → ACX mastering (audio.py)
                                         │
                  chapter WAV + MP3 ──► M4B with chapters, cover, tags
                                         │
                                     report.md
```

## Import (`abtts/books.py`)

- **EPUB**: follows the spine; splits chapters at the table-of-contents anchors (several
  chapters in one HTML file are handled). Removes scripts, images, footnote references
  (`noteref`, `sup a`), footnote and endnote bodies, and page-number spans. Table text is
  kept (signs, letters). The cover image is saved for the M4B.
- **PDF** (PyMuPDF): drops lines in the top/bottom 8% of the page that repeat on at least 30%
  of pages (running headers and footers, digits ignored) and bare page numbers. Chapters come
  from the PDF outline, else from larger-than-body headings or "Chapter …" lines. Paragraphs
  continuing across pages are joined. Line-break hyphens are repaired using the book's own
  word counts, then the macOS word list (`/usr/share/dict/words`): "beau-/tiful" → "beautiful",
  "palm-/trees" stays "palm-trees".
- **TXT / Markdown**: strips the Project Gutenberg header and license, skips the contents
  list, detects headings ("CHAPTER IV", Markdown `#`, short Title Case lines), and joins
  hard-wrapped lines.
- **Cleanup for all formats**: footnote markers (`[1]`, `¹`, trailing `*`), URLs, `[Illustration]`
  captions, `_italics_` underscores, Gutenberg's `{12}` page markers, ornaments (`* * *`),
  small-caps chapter openings ("HIGH above" → "High above"), runs of ALL-CAPS lines merged
  into a sentence ("TRESPASSERS / WILL BE / PROSECUTED"), printer's imprints at the end,
  quotes and dashes normalized.
- Untitled front matter and sections titled Contents/License/Index/Copyright are dropped.
  Everything else is written to `chapters/NN.txt` for the user to review.

## Text normalization (`abtts/textnorm.py`)

Applied at render time, so chapter files stay readable:

- Dates ("31 December 1919" → "the thirty-first of December nineteen nineteen"), times
  ("11:58 p.m." → "eleven fifty-eight PM"), money (£, $, €), percentages, ordinals,
  decades, decimals, years (1100–2099 without a thousands comma, unless followed by a unit).
- Titles and abbreviations (Mr., Dr. + name, St. + name, e.g., i.e., etc., No. 5).
- Shouted phrases lowercased; acronyms up to four letters kept.
- `pronunciations.yaml` (global, then per-project) replaces whole words with respellings.
  Qwen3-TTS has no IPA input; capitalized stressed syllables work well (see `qwen3-tuning.md`).

Testing showed the cloned Base model reads raw numbers correctly, but the preset and
voice-design models did not; normalization is on for everything since it never hurt.

## Chunking (`abtts/chunking.py`)

Paragraphs up to `chunking.max_chars` (500) are one chunk. Longer paragraphs are packed
sentence by sentence; a sentence is never split, even if it is longer than the limit.
Sentence detection skips abbreviations (Mr., Dr., a.m., single initials). See
`chunk-length.md` for why 500.

## Generation and QA (`abtts/engines.py`, `abtts/render.py`)

- `mx.random.seed(seed)` before every chunk; the same base seed for the whole book.
  Combined with one fixed reference clip, the voice stays consistent (speaker-embedding
  similarity ≥ 0.98 between chunks in tuning).
- Each take is edge-trimmed (−50 dB) so the pipeline's pauses are exact.
- Whisper large-v3-turbo transcribes the take. WER is computed after normalizing both
  sides (numbers, dates and times to words, compounds, "hundred and", spelling variants)
  against both the respelled and the original text. Short chunks may have one wrong word.
- Pace check: characters per second against the running median for this narrator;
  < 0.6× suggests long silence or repetition, > 1.6× suggests skipped words.
- Failing takes are regenerated with seed + 7919·attempt, up to `qa.max_retries`; the best
  take is kept and flagged in `report.md` if it still fails.

## Cache and resume (`abtts/project.py`)

Each chunk is stored as `cache/<key>.wav` (32-bit float) + `.json` (text, transcript, WER,
seed, timing). The key is a hash of: text sent to the model, model, voice clip contents and
transcript, language, sampling settings, seed, QA settings and a cache version. Re-running
skips anything with a matching key, so:

- an interrupted run resumes at the next missing chunk,
- editing one paragraph or one pronunciation regenerates only the affected chunks,
- switching voice or temperature regenerates everything, but old takes stay on disk.

`redo` adds a per-chunk seed offset in `book.yaml`, which gives a new key and a fresh take
without touching the old file.

Long runs start `caffeinate -i -s -m -w <pid>` so the Mac doesn't sleep. Progress lines show
percent done, time left and the finish time, extrapolated from this run's throughput.

## Voice delivery (per voice)

A voice's `voice.yaml` may contain `delivery:` (temperature, `pause_stretch`, `pitch`,
`tempo`, `eq`), fitted so narration matches the voice's demo clip (`docs/voice-matching.md`).
The temperature feeds generation unless a book or the command line sets one. The rest is
applied after generation: pauses inside each chunk are lengthened during chapter assembly,
and pitch, tempo and the tone EQ are applied at the start of mastering. Because none of
this changes the chunk cache key, changing it only re-masters chapters (the chapter manifest
includes the delivery values).

## Mastering (`abtts/audio.py`)

Per chapter: resample to 44.1 kHz mono (ffmpeg's swr, 64-tap), 70 Hz high-pass, gain to
an overall RMS of −20 dB, a look-ahead limiter at −3.5 dBFS (re-aimed up to 3 times so RMS
lands within ±0.5 dB), then 0.75 s of head and 2 s of tail room tone, and −70 dB pink-noise
room tone under the whole chapter (ACX rejects pure digital silence). Output: 16-bit WAV.

Measured the way ACX Check does: overall RMS, sample peak, and noise floor as the quietest
0.5 s window. Every chapter's values are in `report.md`.

Exports: MP3 with libmp3lame at 192 kbps CBR, ID3v2.3 tags. M4B: chapters concatenated,
Apple AudioToolbox AAC (`aac_at`) at 128 kbps mono, chapter markers from an FFMETADATA file,
title/author/genre tags and cover art.

## Memory and speed

Qwen3-TTS 1.7B bf16 plus Whisper turbo peak at about 11–13 GB of MLX memory. Measured speed
with QA is about 0.85× real time on the M5 (10-core GPU), so a 10-hour book takes about 8.5 hours.

## Web studio (`webapp/`)

- `webapp/server.py`: FastAPI app served by uvicorn on **127.0.0.1:8765** only. Started by
  `./audiobook.py web` or the `Audiobook Studio.command` launcher.
- **Job queue**: one worker thread runs one job at a time (`render`, `preview`, `redo`, `say`) as
  an `audiobook.py` subprocess with `AUDIOBOOK_EVENTS=1`. The CLI then prints `@@EVENT {json}`
  lines (plan, loading, chunk_start, chunk, mastering, chapter, m4b_start, done), which the server
  turns into live progress. Pause sends SIGINT; the CLI saves and exits cleanly (cached chunks are
  written atomically), and resume is just another `render`.
- **State on disk only**: the library is `projects/*/book.yaml` plus the chunk cache. The server
  caches each book's plan by file modification times so polling stays cheap on long books.
- **Safety**: requests whose Host isn't localhost are refused (DNS rebinding), and every
  non-GET request must carry `X-Studio: 1` (a cross-site page can't add custom headers without a
  CORS preflight, which the server never grants). Book slugs and chapter file names are validated;
  media is served only from `projects/`, `voices/` and `output/web-say/`.
- **Nothing is deleted**: edited chapters are copied to `chapters/history/` first, skipped
  chapters move to `chapters/skipped/`, removed books move to `projects/_archived/`, and
  `pronunciations.yaml` is copied to `logs/pronunciations-history/` before each save.
  `config.yaml` is edited line by line so its comments and alignment survive.
- **Front end**: `webapp/static/` (plain HTML, CSS and JavaScript; no build step, no CDN, works
  offline). Hash routes: library, book, voices, pronunciations, settings. All page text is set
  with `textContent`, never `innerHTML`, so book text can't inject markup. Light and dark follow
  the system setting.
- Uploads go to `books/uploads/`, pasted text to `books/pasted/`, quick-listen audio to
  `output/web-say/` (all git-ignored).

API summary: `GET /api/state`, `GET /api/jobs`, `POST /api/jobs/{id}/cancel`,
`POST /api/projects/upload`, `POST /api/projects/text`, `GET|PATCH /api/projects/{slug}`,
`POST /api/projects/{slug}/render|preview|redo|archive|reveal`,
`GET|PUT /api/projects/{slug}/chapters/{NN.txt}`, `POST …/chapters/{NN.txt}/skip|restore`,
`POST /api/say`, `GET|POST /api/voices`, `POST /api/voices/default`,
`GET|PUT /api/pronunciations`, `GET|PUT /api/settings`.
