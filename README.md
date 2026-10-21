# Audiobook TTS

Turn an ebook into a narrated audiobook on your Mac, entirely offline.

You give it an EPUB, PDF, text or Markdown file. It reads the book in a natural
narrator's voice, checks its own work, fixes mistakes, and gives you:

- one MP3 per chapter (192 kbps, ready for any player)
- one M4B audiobook file with chapter markers, title, author and cover (for Apple Books and audiobook apps)
- a short report telling you which few spots, if any, are worth a listen

The audio meets Audible/ACX technical specs (loudness, peaks, background noise, 44.1 kHz mono).

The narrator is **Qwen3-TTS** (1.7B, full precision) with the voice you picked in the
listening test (`designmale`, temperature 0.9).

---

## Where things are

Everything lives in one folder: **`~/AudiobookTTS`** (the same folder as `~/github/tts`).

| Folder or file | What it is |
|---|---|
| `audiobook.py` | The program you run |
| `config.yaml` | Your settings: voice, model, pauses, quality checks |
| `pronunciations.yaml` | Your list of words to say differently |
| `projects/` | One folder per book (text, audio, results) |
| `voices/` | Narrator voices |
| `docs/` | Technical notes and test results (you don't need these) |

Inside each book's folder, `projects/<book-name>/`:

| | |
|---|---|
| `output/<book>.m4b` | **The finished audiobook** |
| `output/mp3/` | **One MP3 per chapter** |
| `output/wav/` | Full-quality mastered chapters |
| `report.md` | What to listen to, plus speed and loudness numbers |
| `chapters/` | The book's text, one file per chapter. You can edit these. |
| `run.log` | A diary of every run |

---

## Before you start (every time)

Open the **Terminal** app and type:

```bash
cd ~/AudiobookTTS
```

All the commands below are typed in that window, from that folder. Press Return after each one.

Tips for long books:

- **Plug in the charger and leave the lid open.** The program stops the Mac from going to sleep
  while it works, but on battery or with the lid closed macOS may still sleep.
- Quit big apps (browsers with many tabs, Docker or Colima) so the narrator has plenty of memory.
- A 10-hour book takes roughly **8–9 hours**. Starting it in the evening is ideal.

---

## Your first test

A short public-domain book is already imported and waiting: Oscar Wilde's *The Happy Prince
and Other Tales* (5 stories, about 1 hour 45 minutes of audio, about 1 hour 30 minutes to make).
Hear one story first:

```bash
./audiobook.py preview the-happy-prince-and-other-tales --chapter 3
```

Then, if you like it, do the whole book:

```bash
./audiobook.py render the-happy-prince-and-other-tales
```

## Start a new book

The simple way, doing everything in one go:

```bash
./audiobook.py make ~/Downloads/MyBook.epub
```

It shows the chapters it found, then starts narrating. Each line shows progress and an
estimated finish time, like this:

```
[42/610] 03-012  18.4s audio | 6.9% | 7h 52m left, done about Wed 06:40
```

When it finishes it prints where the audiobook is.

**The careful way** (recommended for a new kind of book) is to check the chapters first:

```bash
./audiobook.py new ~/Downloads/MyBook.epub
```

This only reads the book. Look in `projects/<book-name>/chapters/`. Each chapter is a plain
text file you can open in TextEdit. Delete a file to skip that chapter (for example an index
or "About the Author"), fix any odd text, then start narrating:

```bash
./audiobook.py render <book-name>
```

`<book-name>` is the folder name shown by the `new` command, for example `the-happy-prince-and-other-tales`.

To see which chapters a file contains without creating anything:

```bash
./audiobook.py chapters ~/Downloads/MyBook.epub
```

## Try one chapter first

To hear how a book will sound before committing a whole night to it:

```bash
./audiobook.py preview ~/Downloads/MyBook.epub --chapter 1
```

The MP3 lands in `projects/<book-name>/output/preview/mp3/`. Nothing is wasted: when you
narrate the full book later, that chapter is already done.

## Resume an interrupted book

If the Mac restarted, the battery died, or you pressed Control-C, run the same command again:

```bash
./audiobook.py render <book-name>
```

Every finished piece is saved the moment it's made, so it carries on where it stopped. To see
how far along a book is:

```bash
./audiobook.py status <book-name>
```

## Listen to the spots that need it

The program transcribes every piece it narrates and compares it with the book. If a piece has
wrong or missing words, or an odd pace (a long silence or a rushed bit), it automatically
re-records it, up to three times, and keeps the best take.

Anything still not right is listed in **`projects/<book-name>/report.md`**, with the chunk ID
(like `03-012` = chapter 3, piece 12), the text, what was actually heard, and the audio file to
play. Usually there are none or just a few. Unusual names often show up here because the
checker can't spell them, even when they sound fine.

## Fix a mispronunciation

1. Open **`pronunciations.yaml`** (in `~/AudiobookTTS`) in TextEdit.
2. Add a line with the word as written in the book, a colon, then how to say it. Spell it the
   way it sounds, with hyphens between syllables and the **stressed syllable in capitals**:

   ```yaml
   Aoife: Eefa
   Szczepańska: Shcheh-PAHN-ska
   Hermione: her-MY-oh-nee
   ```

3. Save, and run the book again (`./audiobook.py render <book-name>`). Only the pieces containing
   that word are re-recorded; everything else is reused.

To fix a word for just one book, put a `pronunciations.yaml` inside that book's project folder
instead. It's used on top of the main one.

To change actual text (a typo in the ebook, say), edit the file in `projects/<book-name>/chapters/`
and run `render` again. Only the changed paragraphs are re-recorded.

## Re-record a single piece

If something sounds off when you listen (a strange emphasis, a cough-like glitch), find its ID
in `report.md`, or work it out from the chapter and its position, and run:

```bash
./audiobook.py redo <book-name> 03-012
```

You can list several IDs at once: `./audiobook.py redo <book-name> 03-012 05-101`. It makes a
fresh take (the old one is kept, never deleted), rebuilds that chapter's MP3, and rebuilds the
M4B if the whole book is finished.
If you don't like the new take either, run `redo` again for another.

## Switch the voice or model

All of these are in **`config.yaml`**. Open it in TextEdit, change the line, and save.

**Another narrator voice.** See the voices you have:

```bash
./audiobook.py voice list
```

Then change `voice: designmale` to another name, for example `voice: deepbaritone`. The ones from
the listening test are `designmale` (your pick), `deepbaritone`, `britishmale`, `warmfemale`
and `designfemale`.

**Qwen's built-in speakers** (Ryan or Aiden): set `voice: preset:Ryan` or `voice: preset:Aiden`.
The right model is chosen for you.

**Your own voice, or one you have permission to use.** Record 10–30 seconds of calm reading
in a quiet room (no music, no echo, one speaker), save it as a WAV, and write down exactly what
you said. Then:

```bash
./audiobook.py voice add ~/Desktop/myvoice.wav --name me --transcript "The exact words I said in the clip."
```

The clip is cleaned up automatically (silence trimmed, volume evened out). Then set `voice: me`.
Your personal clips are never uploaded to GitHub.

**Livelier or steadier reading**: `temperature` under `sampling:` (0.9 now). Lower (0.7) is calmer
and more even; higher is more varied.

**One-off change for a single run**, without editing the file:

```bash
./audiobook.py preview <book-name> --chapter 2 --voice deepbaritone
```

Changing the voice or temperature re-records the book from scratch (the old recordings stay on
disk, so switching back is instant).

**Model**: the `model:` line. The default is the best-quality Qwen3-TTS. A faster, slightly lower
quality option is `mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit`. Download it once with
`uv run python scripts/download_models.py fast`, then put that name on the `model:` line.

## Pauses and other settings

`config.yaml` also controls:

- **pauses**: 0.35 s inside paragraphs, 0.7 s between paragraphs, 1.75 s after chapter titles
- **numbers**: whether "1923" is read as "nineteen twenty-three" (on) and American style
  "two hundred fifty" vs British "two hundred and fifty"
- **quality checks**: how strict they are, and how many retries
- **chapter room tone**: 0.75 s at the start and 2 s at the end of each chapter (ACX limits are 0.5–1 s and 1–5 s)

Each setting has a short comment next to it.

---

## If something goes wrong

| Problem | What to do |
|---|---|
| `Environment missing` | Run `uv sync --locked` once in `~/AudiobookTTS`. |
| A model is missing or says it is downloading | Run `uv run python scripts/download_models.py core` (about 15 GB, one time). |
| Chapters look wrong (the license or table of contents shows up as a chapter) | Use `new` instead of `make`, delete the unwanted files in `chapters/`, then `render`. |
| It's much slower than usual | Close other apps, plug in power, and check Activity Monitor → Memory for pressure. |
| `A project named ... already exists` | The book was already imported. Use `render <book-name>` to continue it, or add `--name another-name` to start over separately. |
| A PDF reads badly | PDFs vary a lot. If the book also exists as EPUB, use the EPUB. Scanned (image-only) PDFs have no text to read. |

## Limitations

- **English only** is set up and tested. Qwen3-TTS speaks other languages too, but the number
  and abbreviation rules here are English.
- **One narrator voice per book.** No automatic character voices.
- **Footnotes are dropped**, not read.
- **Tables, figures and images are skipped**, except short signs and inscriptions.
- The quality check can't judge acting or emphasis, only words and pacing. Listen to a preview
  chapter before a long run.
- Speed: about 0.85× real time with checks. Ten hours of audio take about eight and a half
  hours to make.

---

## For the technically curious

- [docs/how-it-works.md](docs/how-it-works.md): the pipeline, caching and quality checks
- [docs/setup.md](docs/setup.md): rebuilding the environment, pinned versions
- [docs/](docs/): model research, benchmarks, listening tests and decisions
- [AGENTS.md](AGENTS.md): rules for anyone (or any tool) changing this repository
