"""Book projects: import, plan, cached rendering, chapter mastering, MP3/M4B export, report.

Project layout (projects/<slug>/):
  book.yaml          title, author, source file, optional per-book settings and chunk redos
  source/            a copy of the original book file
  chapters/NN.txt    cleaned chapter text, one paragraph per blank-line block. Edit freely.
  cache/             one WAV + JSON per generated chunk, named by a hash of its text and settings
  output/wav/        mastered chapter WAVs (ACX: 44.1 kHz mono)
  output/mp3/        one 192 kbps CBR MP3 per chapter
  output/*.m4b       the whole book with chapter markers
  report.md          speed, ACX measurements and every chunk that still needs a listen
"""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf
import yaml

from . import audio as A
from .books import read_book, spoken_title
from .chunking import chunk_paragraph
from .engines import Engine, Voice
from .render import PaceTracker, QAConfig, render_chunk
from .textnorm import normalize_for_tts
from .voice import load_voice

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"
VOICES = ROOT / "voices"
CACHE_VERSION = 1  # bump when generation code changes in a way that should invalidate the cache


# ----------------------------------------------------------------------------- settings


def deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_settings(project: Path | None = None, overrides: dict | None = None) -> dict:
    settings = yaml.safe_load((ROOT / "config.yaml").read_text())
    if project and (project / "book.yaml").exists():
        settings = deep_merge(settings, yaml.safe_load((project / "book.yaml").read_text()).get("settings") or {})
    settings = deep_merge(settings, overrides or {})
    # Built-in speakers (voice: preset:Ryan) live in the CustomVoice model, not the Base model.
    if str(settings["voice"]).startswith("preset:") and "-Base" in settings["model"]:
        settings["model"] = settings["model"].replace("-Base", "-CustomVoice")
        settings.setdefault("instruct", PRESET_INSTRUCT)
    return settings


PRESET_INSTRUCT = "Calm, warm, measured audiobook narration with natural pauses."


def load_pronunciations(project: Path | None = None) -> dict:
    pron = {}
    for path in (ROOT / "pronunciations.yaml", project / "pronunciations.yaml" if project else None):
        if path and path.exists():
            pron.update(yaml.safe_load(path.read_text()) or {})
    return {str(k): str(v) for k, v in pron.items()}


# ----------------------------------------------------------------------------- import


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "book"


def import_book(source: Path, name: str | None = None, title: str | None = None,
                author: str | None = None) -> Path:
    """Create projects/<slug>/ from a book file. Never modifies the source file."""
    source = source.expanduser().resolve()
    book = read_book(source)
    slug = slugify(name or title or book.title)
    project = PROJECTS / slug
    if (project / "book.yaml").exists():
        raise FileExistsError(
            f"A project named '{slug}' already exists at {project}. "
            "Resume it with `audiobook.py render` or pass --name to make a new one."
        )
    (project / "source").mkdir(parents=True, exist_ok=True)
    (project / "chapters").mkdir(exist_ok=True)
    shutil.copy2(source, project / "source" / source.name)
    cover = None
    if book.cover:
        cover = f"cover.{book.cover_ext}"
        (project / cover).write_bytes(book.cover)
    for n, ch in enumerate(book.chapters, 1):
        body = "\n\n".join(ch["paragraphs"])
        (project / "chapters" / f"{n:02d}.txt").write_text(f"# {ch['title']}\n\n{body}\n", encoding="utf-8")
    meta = {
        "title": title or book.title,
        "author": author or book.author,
        "source": str(project / "source" / source.name),
        "original_file": str(source),
        "cover": cover,
        "created": dt.datetime.now().isoformat(timespec="seconds"),
        "settings": {},
        "redo": {},
    }
    (project / "book.yaml").write_text(yaml.safe_dump(meta, sort_keys=False, allow_unicode=True))
    return project


def find_project(target: str) -> Path:
    """Accept a project folder, a project name, or the original book file."""
    p = Path(target).expanduser()
    if (p / "book.yaml").exists():
        return p.resolve()
    if (PROJECTS / target / "book.yaml").exists():
        return PROJECTS / target
    if p.is_file():
        resolved = str(p.resolve())
        for meta_path in PROJECTS.glob("*/book.yaml"):
            meta = yaml.safe_load(meta_path.read_text())
            if meta.get("original_file") == resolved:
                return meta_path.parent
    raise FileNotFoundError(f"No project found for '{target}'.")


def project_for(target: str, **import_kwargs) -> tuple[Path, bool]:
    """Find an existing project for target, or import it. Returns (project, created)."""
    try:
        return find_project(target), False
    except FileNotFoundError:
        p = Path(target).expanduser()
        if p.is_file():
            return import_book(p, **import_kwargs), True
        raise


def read_chapters(project: Path) -> list[dict]:
    chapters = []
    for path in sorted((project / "chapters").glob("*.txt")):
        text = path.read_text(encoding="utf-8").strip()
        lines = text.split("\n", 1)
        title = lines[0].lstrip("#").strip() if lines[0].startswith("#") else path.stem
        body = lines[1] if lines[0].startswith("#") and len(lines) > 1 else text
        paragraphs = [" ".join(p.split()) for p in re.split(r"\n\s*\n", body) if p.strip()]
        chapters.append({"number": int(re.sub(r"\D", "", path.stem) or 0), "file": path.name,
                         "title": title, "paragraphs": paragraphs})
    return chapters


# ----------------------------------------------------------------------------- plan


@dataclass
class Chunk:
    chapter: int
    index: int
    text: str  # what the model is given (normalized, respelled)
    original: str  # what the book says (for QA scoring)
    pause_after: float
    key: str = ""
    seed_offset: int = 0

    @property
    def id(self) -> str:
        return f"{self.chapter:02d}-{self.index:03d}"


def file_hash(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def voice_spec(settings: dict) -> tuple[Voice, str]:
    """Build the Voice and a fingerprint of it (clip contents + transcript)."""
    name = settings["voice"]
    if isinstance(name, str) and name.startswith("preset:"):
        voice = Voice(speaker=name.split(":", 1)[1], instruct=settings.get("instruct"))
        return voice, f"preset:{voice.speaker}:{voice.instruct}"
    info = load_voice(name, VOICES)
    ref = info["files"]["24k_mono"]
    return Voice(ref_audio=ref, ref_text=info["transcript"]), f"{name}:{file_hash(ref)}:{info['transcript']}"


def build_plan(project: Path, settings: dict, chapters_wanted: list[int] | None = None) -> list[Chunk]:
    pron = load_pronunciations(project)
    t = settings["text"]
    _, voice_fp = voice_spec(settings)
    meta = yaml.safe_load((project / "book.yaml").read_text())
    redo = meta.get("redo") or {}
    pauses = settings["pauses"]

    def tts(text: str, with_pron: bool = True) -> str:
        return normalize_for_tts(text, numbers=t["expand_numbers"], abbreviations=t["expand_abbreviations"],
                                 american=t["american_numbers"], pronunciations=pron if with_pron else None)

    plan: list[Chunk] = []
    for ch in read_chapters(project):
        if chapters_wanted and ch["number"] not in chapters_wanted:
            continue
        title = spoken_title(ch["title"])
        items = []
        if settings.get("speak_titles", True):
            items.append(Chunk(ch["number"], 0, tts(title), tts(title, False), pauses["after_title"]))
        for para in ch["paragraphs"]:
            pieces = chunk_paragraph(tts(para), settings["chunking"]["max_chars"])
            original = tts(para, False)
            for i, piece in enumerate(pieces):
                last = i == len(pieces) - 1
                items.append(Chunk(ch["number"], len(items), piece, original if len(pieces) == 1 else piece,
                                   pauses["paragraph"] if last else pauses["sentence"]))
        plan.extend(items)

    for c in plan:
        base = {
            "v": CACHE_VERSION, "text": c.text, "model": settings["model"], "voice": voice_fp,
            "language": settings["language"], "sampling": settings["sampling"], "seed": settings["seed"],
            "qa": {k: settings["qa"][k] for k in ("enabled", "wer_threshold", "max_retries")},
        }
        text_key = hashlib.sha256(json.dumps(base, sort_keys=True).encode()).hexdigest()[:20]
        c.seed_offset = int(redo.get(text_key, 0))
        c.key = text_key if not c.seed_offset else f"{text_key}-r{c.seed_offset}"
    return plan


# ----------------------------------------------------------------------------- cache


def cache_paths(project: Path, chunk: Chunk) -> tuple[Path, Path]:
    d = project / "cache"
    return d / f"{chunk.key}.wav", d / f"{chunk.key}.json"


def is_cached(project: Path, chunk: Chunk) -> bool:
    wav, meta = cache_paths(project, chunk)
    return wav.exists() and meta.exists()


def save_chunk(project: Path, chunk: Chunk, take, takes):
    wav, meta = cache_paths(project, chunk)
    wav.parent.mkdir(parents=True, exist_ok=True)
    tmp = wav.with_suffix(".tmp.wav")
    sf.write(str(tmp), take.audio, take.sample_rate, subtype="FLOAT")
    tmp.replace(wav)
    info = {
        "id": chunk.id, "chapter": chunk.chapter, "index": chunk.index, "text": chunk.text,
        "original": chunk.original, "seed": take.seed, "seconds": round(take.seconds, 3),
        "cps": round(take.cps, 2), "wer": round(take.wer, 4), "transcript": take.transcript,
        "problems": take.problems, "attempts": len(takes),
        "generation_seconds": round(sum(t.gen_seconds for t in takes), 2),
        "created": dt.datetime.now().isoformat(timespec="seconds"),
    }
    meta.write_text(json.dumps(info, indent=2, ensure_ascii=False))


def chunk_info(project: Path, chunk: Chunk) -> dict | None:
    _, meta = cache_paths(project, chunk)
    return json.loads(meta.read_text()) if meta.exists() else None


# ----------------------------------------------------------------------------- rendering


def keep_awake():
    """Stop the Mac sleeping (idle and system sleep) for as long as this process runs."""
    if sys.platform == "darwin" and shutil.which("caffeinate"):
        return subprocess.Popen(["caffeinate", "-i", "-s", "-m", "-w", str(os.getpid())])
    return None


def fmt_duration(seconds: float) -> str:
    seconds = int(max(seconds, 0))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"


def _noop(_event: dict):
    pass


def generate(project: Path, plan: list[Chunk], settings: dict, log=print, event=_noop) -> dict:
    """Generate every uncached chunk. Safe to interrupt; finished chunks stay cached."""
    todo = [c for c in plan if not is_cached(project, c)]
    total_chars = sum(len(c.text) for c in plan)
    todo_chars = sum(len(c.text) for c in todo)
    stats = {"generated": 0, "flagged": 0, "gen_seconds": 0.0, "audio_seconds": 0.0}
    log(f"{len(plan)} chunks in plan, {len(plan) - len(todo)} already done, {len(todo)} to generate "
        f"({todo_chars:,} of {total_chars:,} characters).")
    event({"type": "plan", "chunks": len(plan), "done": len(plan) - len(todo), "todo": len(todo),
           "chars": total_chars, "todo_chars": todo_chars})
    if not todo:
        return stats

    voice, _ = voice_spec(settings)
    engine = Engine(settings["model"], voice=voice, sampling=dict(settings["sampling"]),
                    language=settings["language"])
    qa_cfg = settings["qa"]
    qa = QAConfig(wer_threshold=qa_cfg["wer_threshold"], max_retries=qa_cfg["max_retries"],
                  pace_low=qa_cfg["pace_low"], pace_high=qa_cfg["pace_high"], enabled=qa_cfg["enabled"])
    stt = None
    if qa.enabled:
        from .qa import Transcriber

        stt = Transcriber()
    # Seed the pace tracker with this book's finished chunks so pace checks start calibrated.
    done_cps = [i["cps"] for c in plan if (i := chunk_info(project, c)) and not i["problems"] and len(c.text) >= 40]
    pace = PaceTracker(done_cps[-200:])

    log(f"Loading {settings['model']} ...")
    event({"type": "loading"})
    engine.load()
    start = time.time()
    done_chars = 0
    for n, chunk in enumerate(todo, 1):
        event({"type": "chunk_start", "id": chunk.id, "n": n, "todo": len(todo), "text": chunk.text[:160]})
        try:
            best, takes = render_chunk(engine, chunk.text, seed=settings["seed"] + chunk.seed_offset * 104729,
                                       stt=stt, qa=qa, pace=pace, alt_references=[chunk.original])
        except Exception as exc:  # keep going; the chapter is reported as incomplete
            log(f"  [{chunk.id}] FAILED: {type(exc).__name__}: {exc}")
            stats["flagged"] += 1
            continue
        save_chunk(project, chunk, best, takes)
        stats["generated"] += 1
        stats["gen_seconds"] += sum(t.gen_seconds for t in takes)
        stats["audio_seconds"] += best.seconds
        stats["flagged"] += bool(best.problems)
        done_chars += len(chunk.text)
        elapsed = time.time() - start
        remaining = elapsed / done_chars * (todo_chars - done_chars)
        eta = dt.datetime.now() + dt.timedelta(seconds=remaining)
        note = f"  FLAGGED: {'; '.join(best.problems)}" if best.problems else ""
        retry = f" ({len(takes)} takes)" if len(takes) > 1 else ""
        event({"type": "chunk", "id": chunk.id, "n": n, "todo": len(todo), "seconds": round(best.seconds, 1),
               "takes": len(takes), "problems": best.problems, "pct": round(100 * done_chars / todo_chars, 2),
               "eta_seconds": round(remaining), "eta_clock": f"{eta:%a %H:%M}",
               "overall_done": len(plan) - len(todo) + n, "overall_total": len(plan)})
        log(f"[{n}/{len(todo)}] {chunk.id} {best.seconds:5.1f}s audio{retry} | "
            f"{100 * done_chars / todo_chars:5.1f}% | {fmt_duration(remaining)} left, "
            f"done about {eta:%a %H:%M}{note}")
    engine.unload()
    return stats


# ----------------------------------------------------------------------------- assembly


def chapter_audio(project: Path, chunks: list[Chunk]) -> tuple[np.ndarray, int] | None:
    pieces, sr = [], None
    for i, c in enumerate(chunks):
        wav, _ = cache_paths(project, c)
        if not wav.exists():
            return None
        audio, sr = sf.read(str(wav), dtype="float32")
        pieces.append(audio)
        if i < len(chunks) - 1:
            pieces.append(A.silence(c.pause_after, sr))
    return np.concatenate(pieces), sr


def output_name(number: int, title: str) -> str:
    clean = re.sub(r"[^\w\s,'-]", "", title).strip()[:60]
    return f"{number:02d} - {clean}"


def assemble(project: Path, plan: list[Chunk], settings: dict, log=print, out_dir: Path | None = None,
             event=_noop) -> list[dict]:
    """Master and export every chapter whose chunks are all generated."""
    meta = yaml.safe_load((project / "book.yaml").read_text())
    titles = {c["number"]: c["title"] for c in read_chapters(project)}
    out_dir = out_dir or project / "output"
    m = settings["mastering"]
    results = []
    for number in sorted({c.chapter for c in plan}):
        chunks = [c for c in plan if c.chapter == number]
        name = output_name(number, titles.get(number, f"Chapter {number}"))
        wav_out = out_dir / "wav" / f"{name}.wav"
        mp3_out = out_dir / "mp3" / f"{name}.mp3"
        manifest = {"chunks": [c.key for c in chunks], "pauses": [c.pause_after for c in chunks],
                    "mastering": m, "bitrate": settings["output"]["mp3_bitrate"], "title": meta["title"]}
        man_path = out_dir / "wav" / f".{number:02d}.manifest.json"
        if wav_out.exists() and mp3_out.exists() and man_path.exists() and json.loads(man_path.read_text()) == manifest:
            results.append(json.loads((out_dir / "wav" / f".{number:02d}.measure.json").read_text()))
            continue
        event({"type": "mastering", "chapter": number})
        joined = chapter_audio(project, chunks)
        if joined is None:
            missing = sum(not is_cached(project, c) for c in chunks)
            log(f"Chapter {number}: {missing} chunk(s) missing, not assembled.")
            results.append({"chapter": number, "title": titles.get(number), "complete": False})
            continue
        audio, sr = joined
        raw = out_dir / "wav" / f".{number:02d}.raw.wav"
        raw.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(raw), audio, sr, subtype="FLOAT")
        measured = A.master_acx(raw, wav_out, head_s=m["head_seconds"], tail_s=m["tail_seconds"],
                                target_rms_db=m["target_rms_db"])
        raw.unlink()
        mp3_out.parent.mkdir(parents=True, exist_ok=True)
        A.ffmpeg("-i", str(wav_out), "-c:a", "libmp3lame", "-b:a", settings["output"]["mp3_bitrate"],
                 "-ar", "44100", "-ac", "1",
                 "-metadata", f"title={titles.get(number)}", "-metadata", f"artist={meta['author']}",
                 "-metadata", f"album={meta['title']}", "-metadata", f"track={number}",
                 "-metadata", "genre=Audiobook", "-id3v2_version", "3", str(mp3_out))
        result = {"chapter": number, "title": titles.get(number), "complete": True, "wav": str(wav_out),
                  "mp3": str(mp3_out), "acx": measured, "acx_pass": A.acx_pass(measured),
                  "mp3_acx": A.acx_measure(mp3_out), "seconds": measured["seconds"]}
        (out_dir / "wav" / f".{number:02d}.measure.json").write_text(json.dumps(result, indent=2))
        man_path.write_text(json.dumps(manifest))
        event({"type": "chapter", "chapter": number, "acx_pass": result["acx_pass"], "mp3": str(mp3_out)})
        log(f"Chapter {number} mastered: RMS {measured['rms_db']} dB, peak {measured['peak_db']} dB, "
            f"noise floor {measured['noise_floor_db']} dB ({'ACX pass' if result['acx_pass'] else 'ACX FAIL'})")
        results.append(result)
    return results


def make_m4b(project: Path, chapters: list[dict], settings: dict, log=print) -> Path | None:
    if not chapters or not all(c.get("complete") for c in chapters):
        log("M4B skipped: not every chapter is finished yet.")
        return None
    meta = yaml.safe_load((project / "book.yaml").read_text())
    out = project / "output" / f"{slugify(meta['title'])}.m4b"
    inputs = [Path(c["wav"]) for c in chapters] + [project / "book.yaml"]
    if meta.get("cover"):
        inputs.append(project / meta["cover"])
    if out.exists() and all(p.stat().st_mtime < out.stat().st_mtime for p in inputs if p.exists()):
        log(f"M4B up to date: {out}")
        return out
    lines = [";FFMETADATA1", f"title={meta['title']}", f"album={meta['title']}", f"artist={meta['author']}",
             f"album_artist={meta['author']}", "genre=Audiobook", ""]
    concat = ["ffconcat version 1.0"]
    pos = 0
    for c in chapters:
        dur_ms = int(round(A.duration(c["wav"]) * 1000))
        lines += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={pos}", f"END={pos + dur_ms}", f"title={c['title']}", ""]
        pos += dur_ms
        concat.append("file '" + c["wav"].replace("'", "'\\''") + "'")
    work = project / "output" / ".m4b"
    work.mkdir(parents=True, exist_ok=True)
    (work / "chapters.txt").write_text("\n".join(lines))
    (work / "list.ffconcat").write_text("\n".join(concat) + "\n")
    tmp = out.with_suffix(".tmp.m4b")
    args = ["-f", "concat", "-safe", "0", "-i", str(work / "list.ffconcat"), "-i", str(work / "chapters.txt")]
    cover = project / meta["cover"] if meta.get("cover") else None
    if cover and cover.exists():
        args += ["-i", str(cover), "-map", "0:a", "-map", "2:v", "-c:v", "copy", "-disposition:v", "attached_pic"]
    else:
        args += ["-map", "0:a"]
    args += ["-map_metadata", "1", "-map_chapters", "1", "-c:a", "aac_at", "-b:a", settings["output"]["m4b_bitrate"],
             "-ac", "1", "-ar", "44100", "-movflags", "+faststart", "-f", "mp4", str(tmp)]
    A.ffmpeg(*args)
    tmp.replace(out)
    log(f"M4B written: {out} ({fmt_duration(pos / 1000)}, {len(chapters)} chapter{'s' if len(chapters) != 1 else ''})")
    return out


# ----------------------------------------------------------------------------- report


def write_report(project: Path, plan: list[Chunk], chapters: list[dict], settings: dict,
                 run_stats: dict | None = None, m4b: Path | None = None, path: Path | None = None) -> Path:
    meta = yaml.safe_load((project / "book.yaml").read_text())
    infos = [(c, chunk_info(project, c)) for c in plan]
    done = [(c, i) for c, i in infos if i]
    flagged = [(c, i) for c, i in done if i["problems"]]
    missing = [c for c, i in infos if not i]
    gen = sum(i["generation_seconds"] for _, i in done)
    aud = sum(i["seconds"] for _, i in done)
    lines = [
        f"# Report: {meta['title']}", "",
        f"Generated {dt.datetime.now():%Y-%m-%d %H:%M}. Model `{settings['model']}`, voice `{settings['voice']}`, "
        f"temperature {settings['sampling']['temperature']}, seed {settings['seed']}.", "",
        "## Summary", "",
        f"- Chunks: {len(done)} of {len(plan)} generated; {len(flagged)} flagged; {len(missing)} missing",
        f"- Speech generated: {fmt_duration(aud)} in {fmt_duration(gen)} of compute "
        f"(real-time factor {gen / aud:.2f})" if aud else "- Speech generated: none yet",
        f"- Chunks that needed retries: {sum(1 for _, i in done if i['attempts'] > 1)}",
    ]
    if run_stats and run_stats.get("generated"):
        lines.append(f"- This run: {run_stats['generated']} chunks, {fmt_duration(run_stats['audio_seconds'])} of speech "
                     f"in {fmt_duration(run_stats['gen_seconds'])}")
    if m4b:
        lines.append(f"- Audiobook: `{m4b}`")
    lines += ["", "## Chapters (ACX check)", "",
              "| # | Title | Length | RMS (−23…−18) | Peak (≤ −3) | Noise floor (≤ −60) | ACX | MP3 peak |",
              "|---|---|---:|---:|---:|---:|---|---:|"]
    for c in chapters:
        if not c.get("complete"):
            lines.append(f"| {c['chapter']} | {c.get('title')} | not finished | | | | | |")
            continue
        a = c["acx"]
        lines.append(f"| {c['chapter']} | {c['title']} | {fmt_duration(c['seconds'])} | {a['rms_db']} dB | "
                     f"{a['peak_db']} dB | {a['noise_floor_db']} dB | {'pass' if c['acx_pass'] else 'FAIL'} | "
                     f"{c['mp3_acx']['peak_db']} dB |")
    lines += ["", "## Chunks to listen to", ""]
    if not flagged:
        lines.append("None. Every chunk passed the automatic checks.")
    else:
        lines.append("These still failed a check after all retries. Listen to the file; if it sounds wrong, run "
                     "`./audiobook.py redo <project> <ID>` (or fix the text in `chapters/`).")
        lines.append("")
        for c, i in flagged:
            wav, _ = cache_paths(project, c)
            lines += [f"### {c.id}: {'; '.join(i['problems'])}", "",
                      f"- Text: {c.text}", f"- Heard: {i['transcript']}", f"- File: `{wav}`", ""]
    path = path or project / "report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    return path


# ----------------------------------------------------------------------------- redo


def redo_chunk(project: Path, chunk_id: str, settings: dict) -> Chunk:
    """Ask for a fresh take of one chunk. The old take stays in cache/ untouched."""
    plan = build_plan(project, settings)
    match = [c for c in plan if c.id == chunk_id]
    if not match:
        raise KeyError(f"No chunk {chunk_id}. IDs look like 03-012 (chapter 3, chunk 12); see report.md.")
    chunk = match[0]
    base_key = chunk.key.split("-r")[0]
    meta_path = project / "book.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    redo = meta.get("redo") or {}
    redo[base_key] = int(redo.get(base_key, 0)) + 1
    meta["redo"] = redo
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False, allow_unicode=True))
    return chunk
