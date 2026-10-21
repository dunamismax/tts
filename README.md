# Audiobook TTS

Turn an ebook, or any text you paste, into a narrated audiobook on your Mac, entirely offline.

You get:

- one MP3 per chapter (192 kbps, ready for any player)
- one M4B audiobook file with chapter markers, title, author and cover (for Apple Books and audiobook apps)
- a short list of the few spots, if any, worth a listen

The audio meets Audible/ACX technical specs (loudness, peaks, background noise, 44.1 kHz mono).
The narrator is **Qwen3-TTS** (1.7B, full precision) reading in **British Male**
(`britishmale`): a refined British (RP) voice in his fifties, smooth, mellow and intimate.
That's the voice you chose, tuned so whole books sound like its sample on the Voices page:
the same unhurried pace, pauses, pitch and tone.

---

## Open the studio

In Finder, open your **AudiobookTTS** folder (in your home folder) and **double-click
`Audiobook Studio.command`**.

A Terminal window opens and **Audiobook Studio** appears in your web browser. Leave the Terminal
window open while you use the studio (minimize it if you like). Closing it stops the studio, and
pauses any narration that's running.

Tip: drag `Audiobook Studio.command` onto the Dock (right-hand side) to open it with one click.

The studio only runs on your Mac (`http://127.0.0.1:8765`). Nothing is uploaded anywhere.

---

## Make an audiobook

### From a book file

On the **Library** page, drag an **EPUB, PDF, TXT or Markdown** file anywhere onto the window, or
click **choose a file**. The studio reads the book, finds the chapters and opens the book's page.

### From text you paste

Click **Paste text**, give it a title, paste your text, and choose:

- **Listen now**: narrates it straight away as a single track and plays it. Good for an article
  or a few pages.
- **Create audiobook**: makes it a book in your library, with chapters if your text has lines
  like "Chapter 2" or "## Part Two".

### On the book's page

1. **Check the chapters.** Each row shows a chapter and how it starts. Use the pencil to fix the
   text, or the crossed-out eye to **skip** a chapter (for example an index or "About the Author").
   Skipped chapters can be restored any time.
2. **Hear a sample.** The headphones button on a chapter (or **Preview chapter 1**) narrates just
   that chapter and plays it, so you can check the voice before committing a whole night.
3. **Press Narrate the book.** A progress bar shows how far along it is, how long is left, when it
   will be ready, and the sentence being read right now. You can close the browser tab; it keeps
   going as long as the Terminal window is open.
4. **When it's done**, press **Download audiobook (.m4b)**, or play any chapter in the player at
   the bottom of the window. **Show in Finder** takes you to the files.

A 10-hour book takes about **8–9 hours**. For long books: keep the Mac plugged in with the lid
open, and quit big apps (browsers with many tabs, Docker or Colima) so the narrator has plenty of
memory. The studio keeps the Mac from going to sleep while it works.

### Pause and resume

Press **Pause** at any time. Everything finished so far is saved, and **Resume narrating** carries
on from the same spot, even after a restart or a dead battery.

### Spots that need a listen

Every piece the narrator reads is transcribed and compared with the book. If words are wrong or
missing, or the pace is odd (a long silence, a rushed bit), that piece is re-recorded
automatically, up to three times, and the best take is kept.

Anything still not right appears under **Needs a listen** on the book's page, with the text, what
was actually heard, and a play button. Usually there are none or just a few. Unusual names often
appear here because the checker can't spell them, even when they sound fine. If one sounds wrong,
press **Re-record** for a fresh take. The old take is kept, and the chapter's files (and the
audiobook file, if the book is finished) are rebuilt.

---

## Fix a mispronunciation

Open **Pronunciations**. Add the word as it's written in the book, and how to say it, spelled the
way it sounds with hyphens between syllables and the **stressed syllable in capitals**:

| In the book | Say it like |
|---|---|
| Hermione | her-MY-oh-nee |
| Aoife | Eefa |
| Szczepańska | Shcheh-PAHN-ska |

Press the headphones to hear it, then **Save**. Next time you narrate, only the pieces containing
that word are re-recorded; everything else is reused.

To change actual words (a typo in the ebook, say), edit the chapter on the book's page. Only the
paragraphs you changed are re-recorded, and the previous version of the chapter is kept.

## Voices

Open **Voices** to play each narrator's sample, **Try it** with your own sentence, and **Make
default** for new books. Each book can also have its own voice: on the book's page, open **Voice &
settings**. There you can also set **Liveliness** (steadier ↔ livelier reading) and whether chapter
titles are read aloud, and press **Hear a sample** to check.

- `britishmale` (your pick, the default), `designmale`, `deepbaritone`, `warmfemale`,
  `designfemale`: narrator voices designed for this project. British Male shows **Matches
  sample**: its narration is tuned to sound like the sample you hear when you press play.
- **Ryan** and **Aiden**: Qwen3's built-in speakers

**Your own voice**, or one you have permission to use: on the Voices page, drop a clip into **Add
your own voice**, type exactly what it says, and give it a name. A good clip is 10–30 seconds of
one person reading calmly in a quiet room: no music, no echo. WAV is best; MP3 and M4A work too.
Silence is trimmed and the volume evened out automatically, and personal clips are never put on
GitHub.

Changing a book's voice or liveliness re-records it from the start. The pieces made in the old
voice stay on disk, so switching back is instant.

## Settings

The **Settings** page sets the defaults for every book: voice, liveliness, the pauses (0.35 s
between sentences in a paragraph, 0.7 s between paragraphs, 1.75 s after a chapter title), whether
titles are read aloud, and how strict the automatic checks are. It also shows your Mac's memory
and free disk space.

---

## Where things are

Everything lives in **`~/AudiobookTTS`** (the same folder as `~/github/tts`).

| Folder or file | What it is |
|---|---|
| `Audiobook Studio.command` | Double-click to open the studio |
| `projects/<book>/output/` | **Finished audiobooks**: the `.m4b`, plus `mp3/` and `wav/` folders |
| `projects/<book>/chapters/` | The book's text, one file per chapter |
| `projects/<book>/report.md` | Speed, loudness measurements and spots to check |
| `projects/_archived/` | Books you removed from the library (nothing is ever deleted) |
| `voices/` | Narrator voices |
| `config.yaml`, `pronunciations.yaml` | Your settings (the studio edits these for you) |
| `docs/` | Technical notes and test results |

A short public-domain book is already in the library for a first test: Oscar Wilde's *The Happy
Prince and Other Tales* (5 stories, about 1 hour 45 minutes of audio, about 1 hour 30 minutes to make).

---

## If something goes wrong

| Problem | What to do |
|---|---|
| Double-clicking the launcher does nothing, or macOS warns about it | Right-click it → **Open** → **Open**. macOS only asks the first time. |
| The browser says it can't connect | The Terminal window was closed. Double-click `Audiobook Studio.command` again. |
| `Environment missing` in the Terminal window | Open Terminal and run `cd ~/AudiobookTTS && uv sync --locked`, once. |
| A model is missing or downloading | In Terminal: `cd ~/AudiobookTTS && uv run python scripts/download_models.py core` (about 15 GB, once). |
| Chapters look wrong (license or contents page shows up) | Skip those chapters on the book's page. |
| It's much slower than usual | Close other apps, plug in power, check Activity Monitor → Memory. |
| A PDF reads badly | PDFs vary a lot; use the EPUB if there is one. Scanned PDFs (pictures of pages) have no text to read. |

## Limitations

- **English only** is set up and tested.
- **One narrator voice per book.** No automatic character voices.
- **Footnotes are dropped**, and tables and images are skipped (short signs and inscriptions are kept).
- The automatic checks catch wrong or missing words and pacing, not acting or emphasis. Preview a
  chapter before a long run.
- One narration runs at a time; others wait in line.

---

## Using Terminal instead (optional)

Everything in the studio is also available as commands. In Terminal, start with `cd ~/AudiobookTTS`.

| Command | What it does |
|---|---|
| `./audiobook.py web` | Opens the studio (same as the launcher) |
| `./audiobook.py make ~/Downloads/MyBook.epub` | Import and narrate a whole book |
| `./audiobook.py new ~/Downloads/MyBook.epub` | Import only, to check chapters first |
| `./audiobook.py render <book-name>` | Narrate or resume an imported book |
| `./audiobook.py preview <book-name> --chapter 3` | Narrate one chapter for a quick listen |
| `./audiobook.py status <book-name>` | How far along a book is |
| `./audiobook.py redo <book-name> 03-012` | Fresh take of one piece (IDs are in `report.md`) |
| `./audiobook.py say "Some text" --out hello.mp3` | Speak a bit of text to a file |
| `./audiobook.py chapters ~/Downloads/MyBook.epub` | Show the chapters a file contains |
| `./audiobook.py voice add clip.wav --name me --transcript "exact words"` | Add a voice |
| `./audiobook.py voice list` | List voices |

Add `--voice NAME` or `--temperature 0.8` to `make`, `render`, `preview` or `say` for a one-off
change. `<book-name>` is the book's folder name in `projects/`.

## For the technically curious

- [docs/how-it-works.md](docs/how-it-works.md): the pipeline, the web studio, caching and quality checks
- [docs/setup.md](docs/setup.md): rebuilding the environment, pinned versions
- [docs/](docs/): model research, benchmarks, listening tests and decisions
- [AGENTS.md](AGENTS.md): rules for anyone (or any tool) changing this repository
