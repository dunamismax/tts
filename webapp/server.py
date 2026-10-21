"""Audiobook Studio: the local web interface for audiobook.py.

Run with `./audiobook.py web` (or double-click "Audiobook Studio.command").
Listens on 127.0.0.1 only. Narration jobs run one at a time, each as an
`audiobook.py` subprocess that reports progress as JSON event lines.
"""

from __future__ import annotations

import collections
import datetime as dt
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

import yaml
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from abtts import project as P  # noqa: E402
from abtts.voice import load_voice, prepare_voice  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
PROJECTS = P.PROJECTS
VOICES = P.VOICES
UPLOADS = ROOT / "books" / "uploads"
PASTED = ROOT / "books" / "pasted"
SAY_DIR = ROOT / "output" / "web-say"
CONFIG = ROOT / "config.yaml"
PRON = ROOT / "pronunciations.yaml"
BOOK_TYPES = {".epub", ".pdf", ".txt", ".md", ".markdown", ".text"}
AUDIO_TYPES = {".wav", ".mp3", ".m4a", ".aiff", ".aif", ".flac", ".caf", ".ogg"}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
CHAPTER_RE = re.compile(r"^\d{1,4}\.txt$")
PRESETS = {
    "Ryan": "Qwen3 built-in speaker. Dynamic male voice with strong rhythmic drive.",
    "Aiden": "Qwen3 built-in speaker. Sunny American male voice with a clear midrange.",
}
NOISE = ("Initialized encoder codebooks", "Loaded speech tokenizer", "Fetching ", "it/s]")


# ----------------------------------------------------------------------------- jobs


class Job:
    def __init__(self, kind: str, args: list[str], label: str, project: str | None = None, extra: dict | None = None):
        self.id = uuid.uuid4().hex[:10]
        self.kind = kind
        self.args = args
        self.label = label
        self.project = project
        self.extra = extra or {}
        self.status = "queued"
        self.created = time.time()
        self.started: float | None = None
        self.finished: float | None = None
        self.progress: dict = {}
        self.result: dict = {}
        self.log: collections.deque[str] = collections.deque(maxlen=400)
        self.proc: subprocess.Popen | None = None
        self.cancel_requested = False

    def to_dict(self, with_log: bool = False) -> dict:
        d = {
            "id": self.id, "kind": self.kind, "label": self.label, "project": self.project,
            "status": self.status, "created": self.created, "started": self.started,
            "finished": self.finished, "progress": self.progress, "result": self.result, "extra": self.extra,
            "last_line": self.log[-1] if self.log else "",
        }
        if with_log:
            d["log"] = list(self.log)
        return d


class JobQueue:
    def __init__(self):
        self.jobs: list[Job] = []
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.stopping = False
        self.thread = threading.Thread(target=self._worker, daemon=True)

    def start(self):
        self.thread.start()

    def add(self, job: Job) -> Job:
        with self.lock:
            self.jobs.append(job)
            # Keep memory bounded: drop old finished jobs.
            finished = [j for j in self.jobs if j.status in {"done", "failed", "cancelled"}]
            for old in finished[:-30]:
                self.jobs.remove(old)
        self.wake.set()
        return job

    def get(self, job_id: str) -> Job | None:
        return next((j for j in self.jobs if j.id == job_id), None)

    def active_for(self, slug: str) -> Job | None:
        return next((j for j in self.jobs if j.project == slug and j.status in {"queued", "running"}), None)

    def running(self) -> Job | None:
        return next((j for j in self.jobs if j.status == "running"), None)

    def cancel(self, job: Job):
        job.cancel_requested = True
        if job.status == "queued":
            job.status = "cancelled"
            job.finished = time.time()
        elif job.status == "running" and job.proc and job.proc.poll() is None:
            job.proc.send_signal(signal.SIGINT)  # audiobook.py saves and exits cleanly

            def force():
                time.sleep(15)
                if job.proc and job.proc.poll() is None:
                    job.proc.kill()

            threading.Thread(target=force, daemon=True).start()

    def shutdown(self):
        self.stopping = True
        for j in list(self.jobs):
            if j.status == "running":
                self.cancel(j)
        self.wake.set()

    def _next(self) -> Job | None:
        with self.lock:
            return next((j for j in self.jobs if j.status == "queued"), None)

    def _worker(self):
        while not self.stopping:
            job = self._next()
            if job is None:
                self.wake.wait(1.0)
                self.wake.clear()
                continue
            self._run(job)

    def _run(self, job: Job):
        job.status = "running"
        job.started = time.time()
        env = {**os.environ, "AUDIOBOOK_EVENTS": "1", "PYTHONUNBUFFERED": "1"}
        cmd = [sys.executable, str(ROOT / "audiobook.py"), *job.args]
        job.log.append("$ audiobook.py " + " ".join(job.args))
        try:
            job.proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True, bufsize=1)
            assert job.proc.stdout
            for line in job.proc.stdout:
                line = line.rstrip()
                if line.startswith("@@EVENT "):
                    try:
                        evt = json.loads(line[8:])
                    except json.JSONDecodeError:
                        continue
                    self._on_event(job, evt)
                elif line and not any(n in line for n in NOISE):
                    job.log.append(line)
            code = job.proc.wait()
        except Exception as exc:  # noqa: BLE001
            job.log.append(f"Error: {exc}")
            code = -1
        job.finished = time.time()
        if job.cancel_requested:
            job.status = "cancelled"
        else:
            job.status = "done" if code == 0 else "failed"
        if job.project:
            SUMMARY_CACHE.pop(job.project, None)

    def _on_event(self, job: Job, evt: dict):
        kind = evt.get("type")
        if kind == "plan":
            job.progress.update({"chunks": evt["chunks"], "done_before": evt["done"], "todo": evt["todo"],
                                 "stage": "starting"})
        elif kind == "loading":
            job.progress["stage"] = "loading"
        elif kind == "chunk_start":
            job.progress.update({"stage": "narrating", "current": evt.get("id"), "current_text": evt.get("text")})
        elif kind == "chunk":
            job.progress.update({k: evt.get(k) for k in ("n", "todo", "pct", "eta_seconds", "eta_clock",
                                                         "overall_done", "overall_total")})
            job.progress["stage"] = "narrating"
            if evt.get("problems"):
                job.progress["flagged"] = job.progress.get("flagged", 0) + 1
            if job.project:
                SUMMARY_CACHE.pop(job.project, None)
        elif kind == "mastering":
            job.progress.update({"stage": "mastering", "chapter": evt.get("chapter")})
        elif kind == "chapter" and job.project:
            SUMMARY_CACHE.pop(job.project, None)
        elif kind == "m4b_start":
            job.progress["stage"] = "packaging"
        elif kind == "done":
            job.result = {k: v for k, v in evt.items() if k != "type"}
            if job.result.get("file"):
                job.result["url"] = media_url(Path(job.result["file"]))
            if job.result.get("previews"):
                job.result["preview_urls"] = [media_url(Path(p)) for p in job.result["previews"]]


QUEUE = JobQueue()


# ----------------------------------------------------------------------------- helpers


def media_url(path: Path) -> str | None:
    path = Path(path).resolve()
    for base, prefix in ((PROJECTS.resolve(), "/media/projects"), (VOICES.resolve(), "/media/voices"),
                         (SAY_DIR.resolve(), "/media/say")):
        try:
            rel = path.relative_to(base)
        except ValueError:
            continue
        return prefix + "/" + "/".join(quote(part) for part in rel.parts) + f"?v={int(path.stat().st_mtime) if path.exists() else 0}"
    return None


def project_dir(slug: str) -> Path:
    if not SLUG_RE.match(slug) or not (PROJECTS / slug / "book.yaml").exists():
        raise HTTPException(404, "No such book.")
    return PROJECTS / slug


def read_meta(project: Path) -> dict:
    return yaml.safe_load((project / "book.yaml").read_text()) or {}


def write_meta(project: Path, meta: dict):
    (project / "book.yaml").write_text(yaml.safe_dump(meta, sort_keys=False, allow_unicode=True))


def safe_name(name: str) -> str:
    base = Path(name or "upload").name
    return re.sub(r"[^\w.\- ]+", "_", base).strip() or "upload"


def unique_slug(title: str) -> str:
    base = P.slugify(title)
    slug, n = base, 2
    while (PROJECTS / slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def config_text() -> str:
    return CONFIG.read_text()


def set_config_value(key: str, value) -> None:
    """Change one setting in config.yaml in place, keeping the comments."""
    text = config_text()
    rendered = "true" if value is True else "false" if value is False else str(value)
    pattern = re.compile(rf"^(\s*{re.escape(key)}:[ \t]*)([^#\n]*?)([ \t]*#.*)?$", re.M)
    if not pattern.search(text):
        raise HTTPException(400, f"Setting '{key}' not found in config.yaml")
    def repl(m):
        if not m.group(3):
            return m.group(1) + rendered
        comment_col = len(m.group(1)) + len(m.group(2)) + len(m.group(3)) - len(m.group(3).lstrip())
        pad = max(2, comment_col - len(m.group(1)) - len(rendered))
        return m.group(1) + rendered + " " * pad + m.group(3).strip()

    text = pattern.sub(repl, text, count=1)
    yaml.safe_load(text)  # refuse to write a broken file
    CONFIG.write_text(text)


# Plans are expensive for long books (text normalization), so cache them by file mtimes.
SUMMARY_CACHE: dict[str, tuple[tuple, list]] = {}


def plan_for(project: Path, settings: dict) -> list:
    files = sorted((project / "chapters").glob("*.txt"))
    pron_files = [PRON, project / "pronunciations.yaml", CONFIG, project / "book.yaml"]
    key = tuple((str(f), f.stat().st_mtime) for f in files + [p for p in pron_files if p.exists()])
    cached = SUMMARY_CACHE.get(project.name)
    if cached and cached[0] == key:
        return cached[1]
    plan = P.build_plan(project, settings)
    SUMMARY_CACHE[project.name] = (key, plan)
    return plan


def find_output(project: Path, number: int, title: str, sub: str = "") -> Path | None:
    out = project / "output" / sub / "mp3" / f"{P.output_name(number, title)}.mp3"
    return out if out.exists() else None


def summarize(slug: str, detail: bool = False) -> dict:
    project = project_dir(slug)
    meta = read_meta(project)
    settings = P.load_settings(project)
    chapters = P.read_chapters(project)
    error = None
    try:
        plan = plan_for(project, settings)
    except Exception as exc:  # noqa: BLE001 (e.g. a voice was removed)
        plan, error = [], str(exc)
    infos = {c.key: P.chunk_info(project, c) for c in plan}
    done = [c for c in plan if infos.get(c.key)]
    flagged = [c for c in done if infos[c.key]["problems"]]
    words = sum(len(p.split()) for ch in chapters for p in ch["paragraphs"])
    gen = sum(infos[c.key]["generation_seconds"] for c in done)
    chars_done = sum(len(c.text) for c in done)
    todo_chars = sum(len(c.text) for c in plan if not infos.get(c.key))
    rate = chars_done / gen if gen > 30 else 14 / 0.9
    audio_done = sum(infos[c.key]["seconds"] for c in done)
    est_audio = audio_done / chars_done * sum(len(c.text) for c in plan) if chars_done > 500 else words / 155 * 60
    tempo = float(settings.get("delivery", {}).get("tempo") or 1.0)
    if chars_done > 500:
        est_audio /= tempo  # cached chunks are pre-tempo; the finished audio is slower
    m4b = next(iter(sorted((project / "output").glob("*.m4b"))), None) if (project / "output").exists() else None
    job = QUEUE.active_for(slug)
    if job and job.status == "running":
        state = "rendering"
    elif job:
        state = "queued"
    elif plan and len(done) == len(plan) and m4b:
        state = "complete"
    elif done:
        state = "partial"
    else:
        state = "new"
    cover = project / meta["cover"] if meta.get("cover") else None
    summary = {
        "slug": slug, "title": meta.get("title"), "author": meta.get("author"),
        "cover": media_url(cover) if cover and cover.exists() else None,
        "created": meta.get("created"), "state": state, "error": error,
        "chapters": len(chapters), "words": words,
        "chunks": len(plan), "chunks_done": len(done), "flagged": len(flagged),
        "est_audio_seconds": round(est_audio), "est_render_seconds": round(todo_chars / rate),
        "m4b": media_url(m4b) if m4b else None, "m4b_name": m4b.name if m4b else None,
        "voice": settings["voice"], "temperature": settings["sampling"]["temperature"],
        "speak_titles": settings.get("speak_titles", True),
        "job": job.to_dict() if job else None,
        "updated": max([(project / "book.yaml").stat().st_mtime] + ([m4b.stat().st_mtime] if m4b else [])),
    }
    if not detail:
        return summary
    by_chapter: dict[int, list] = collections.defaultdict(list)
    for c in plan:
        by_chapter[c.chapter].append(c)
    rows = []
    for ch in chapters:
        cs = by_chapter.get(ch["number"], [])
        mp3 = find_output(project, ch["number"], ch["title"])
        prev = find_output(project, ch["number"], ch["title"], "preview")
        ch_words = sum(len(p.split()) for p in ch["paragraphs"])
        rows.append({
            "number": ch["number"], "file": ch["file"], "title": ch["title"], "words": ch_words,
            "minutes": round(ch_words / 155, 1), "chunks": len(cs),
            "done": sum(1 for c in cs if infos.get(c.key)),
            "flagged": sum(1 for c in cs if infos.get(c.key) and infos[c.key]["problems"]),
            "mp3": media_url(mp3) if mp3 else None, "preview": media_url(prev) if prev else None,
            "first_line": (ch["paragraphs"][0][:160] if ch["paragraphs"] else ""),
        })
    skipped = []
    for f in sorted((project / "chapters" / "skipped").glob("*.txt")) if (project / "chapters" / "skipped").exists() else []:
        first = f.read_text(encoding="utf-8").split("\n", 1)[0].lstrip("# ").strip()
        skipped.append({"file": f.name, "title": first})
    summary["chapter_list"] = rows
    summary["skipped"] = skipped
    summary["flagged_list"] = [{
        "id": c.id, "chapter": c.chapter, "text": c.text, "heard": infos[c.key]["transcript"],
        "problems": infos[c.key]["problems"], "wer": infos[c.key]["wer"],
        "audio": media_url(P.cache_paths(project, c)[0]),
    } for c in flagged]
    recent = [j for j in QUEUE.jobs if j.project == slug]
    summary["last_job"] = recent[-1].to_dict(with_log=True) if recent else None
    return summary


def list_projects() -> list[dict]:
    out = []
    if not PROJECTS.exists():
        return out
    for meta_path in PROJECTS.glob("*/book.yaml"):
        slug = meta_path.parent.name
        if slug.startswith(("_", ".")) or not SLUG_RE.match(slug):
            continue
        try:
            out.append(summarize(slug))
        except Exception as exc:  # noqa: BLE001
            out.append({"slug": slug, "title": slug, "error": str(exc), "state": "error"})
    order = {"rendering": 0, "queued": 1}
    return sorted(out, key=lambda s: (order.get(s.get("state"), 2), -(s.get("updated") or 0)))


def enqueue_render(slug: str, kind: str, extra_args: list[str] | None = None, label: str | None = None,
                   extra: dict | None = None) -> Job:
    if QUEUE.active_for(slug) and kind == "render":
        raise HTTPException(409, "This book is already narrating or waiting in line.")
    args = {"render": ["render", slug], "preview": ["preview", slug], "redo": ["redo", slug]}[kind] + (extra_args or [])
    meta = read_meta(project_dir(slug))
    return QUEUE.add(Job(kind, args, label or meta.get("title", slug), project=slug, extra=extra))


# ----------------------------------------------------------------------------- app


@asynccontextmanager
async def lifespan(_app: FastAPI):
    for d in (PROJECTS, UPLOADS, PASTED, SAY_DIR):
        d.mkdir(parents=True, exist_ok=True)
    QUEUE.start()
    yield
    QUEUE.shutdown()


app = FastAPI(title="Audiobook Studio", lifespan=lifespan, docs_url=None, redoc_url=None)

ALLOWED_HOSTS = {"127.0.0.1", "localhost", "[::1]"}


@app.middleware("http")
async def local_only(request: Request, call_next):
    host = (request.headers.get("host") or "").rsplit(":", 1)[0]
    if host not in ALLOWED_HOSTS:
        return JSONResponse({"detail": "Local access only."}, status_code=403)
    if request.method not in {"GET", "HEAD"} and request.headers.get("x-studio") != "1":
        return JSONResponse({"detail": "Missing studio header."}, status_code=403)
    return await call_next(request)


class TextBook(BaseModel):
    title: str
    author: str = ""
    text: str
    speak_titles: bool = False


class BookPatch(BaseModel):
    title: str | None = None
    author: str | None = None
    voice: str | None = None
    temperature: float | None = None
    speak_titles: bool | None = None


class ChapterText(BaseModel):
    text: str


class Ids(BaseModel):
    ids: list[str]


class ChapterNo(BaseModel):
    chapter: int


class SayRequest(BaseModel):
    text: str
    voice: str | None = None
    temperature: float | None = None
    project: str | None = None
    label: str | None = None


class Pron(BaseModel):
    entries: list[dict]


class Settings(BaseModel):
    voice: str | None = None
    temperature: float | None = None
    sentence: float | None = None
    paragraph: float | None = None
    after_title: float | None = None
    speak_titles: bool | None = None
    wer_threshold: float | None = None
    max_retries: int | None = None


# --- library


@app.get("/api/state")
def state():
    return {"projects": list_projects(), "jobs": [j.to_dict() for j in QUEUE.jobs]}


@app.get("/api/jobs")
def jobs():
    return {"jobs": [j.to_dict() for j in QUEUE.jobs]}


@app.get("/api/jobs/{job_id}")
def job_detail(job_id: str):
    job = QUEUE.get(job_id)
    if not job:
        raise HTTPException(404, "No such job.")
    return job.to_dict(with_log=True)


@app.post("/api/jobs/{job_id}/cancel")
def job_cancel(job_id: str):
    job = QUEUE.get(job_id)
    if not job:
        raise HTTPException(404, "No such job.")
    QUEUE.cancel(job)
    return job.to_dict()


def _import(path: Path, title: str | None, author: str | None) -> dict:
    try:
        from abtts.books import read_book

        book = read_book(path)
        if not book.chapters:
            raise ValueError("No readable text was found in this file. (Scanned PDFs contain only images.)")
        slug = unique_slug(title or book.title)
        project = P.import_book(path, name=slug, title=title or None, author=author or None)
    except (ValueError, FileExistsError) as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"slug": project.name}


@app.post("/api/projects/upload")
def upload_book(file: Annotated[UploadFile, File()], title: Annotated[str, Form()] = "",
                author: Annotated[str, Form()] = ""):
    name = safe_name(file.filename or "book")
    if Path(name).suffix.lower() not in BOOK_TYPES:
        raise HTTPException(400, "Please choose an EPUB, PDF, TXT or Markdown file.")
    dest = UPLOADS / f"{dt.datetime.now():%Y%m%d-%H%M%S}-{name}"
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    return _import(dest, title.strip() or None, author.strip() or None)


@app.post("/api/projects/text")
def paste_book(body: TextBook):
    text = body.text.replace("\r\n", "\n").strip()
    if len(text) < 2:
        raise HTTPException(400, "Paste some text first.")
    title = body.title.strip() or (text.split("\n", 1)[0][:60].strip(" #") or "Untitled")
    slug = unique_slug(title)
    has_headings = bool(re.search(r"^#{1,3}\s+\S|^(chapter|part)\s+\w+", text, re.M | re.I))
    body_md = text if has_headings else f"## {title}\n\n{text}"
    src = PASTED / f"{dt.datetime.now():%Y%m%d-%H%M%S}-{slug}.md"
    src.write_text(f"# {title}\n\n" + (f"By {body.author.strip()}\n\n" if body.author.strip() else "") + body_md + "\n",
                   encoding="utf-8")
    result = _import(src, title, body.author.strip() or None)
    project = PROJECTS / result["slug"]
    meta = read_meta(project)
    meta.setdefault("settings", {})["speak_titles"] = bool(body.speak_titles)
    write_meta(project, meta)
    return result


@app.get("/api/projects/{slug}")
def project_detail(slug: str):
    return summarize(slug, detail=True)


@app.patch("/api/projects/{slug}")
def project_patch(slug: str, body: BookPatch):
    project = project_dir(slug)
    meta = read_meta(project)
    if body.title is not None and body.title.strip():
        meta["title"] = body.title.strip()
    if body.author is not None:
        meta["author"] = body.author.strip() or "Unknown"
    settings = meta.get("settings") or {}
    if body.voice is not None:
        voice_exists(body.voice)
        settings["voice"] = body.voice
    if body.temperature is not None:
        settings.setdefault("sampling", {})["temperature"] = round(max(0.3, min(1.3, body.temperature)), 2)
    if body.speak_titles is not None:
        settings["speak_titles"] = body.speak_titles
    meta["settings"] = settings
    write_meta(project, meta)
    SUMMARY_CACHE.pop(slug, None)
    return summarize(slug, detail=True)


@app.post("/api/projects/{slug}/archive")
def project_archive(slug: str):
    """Remove a book from the library without deleting anything: it moves to projects/_archived/."""
    project = project_dir(slug)
    if QUEUE.active_for(slug):
        raise HTTPException(409, "Pause this book's narration first.")
    dest = PROJECTS / "_archived" / f"{slug}-{dt.datetime.now():%Y%m%d-%H%M%S}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(project), str(dest))
    return {"archived_to": str(dest)}


@app.post("/api/projects/{slug}/reveal")
def project_reveal(slug: str):
    project = project_dir(slug)
    m4b = next(iter(sorted((project / "output").glob("*.m4b"))), None) if (project / "output").exists() else None
    subprocess.run(["open", "-R", str(m4b or project / "chapters")], check=False)
    return {"ok": True}


@app.get("/api/projects/{slug}/chapters/{file}")
def chapter_get(slug: str, file: str):
    project = project_dir(slug)
    if not CHAPTER_RE.match(file):
        raise HTTPException(404, "No such chapter.")
    path = project / "chapters" / file
    if not path.exists():
        raise HTTPException(404, "No such chapter.")
    return {"file": file, "text": path.read_text(encoding="utf-8")}


@app.put("/api/projects/{slug}/chapters/{file}")
def chapter_put(slug: str, file: str, body: ChapterText):
    project = project_dir(slug)
    if not CHAPTER_RE.match(file):
        raise HTTPException(404, "No such chapter.")
    path = project / "chapters" / file
    if not path.exists():
        raise HTTPException(404, "No such chapter.")
    text = body.text.replace("\r\n", "\n").strip() + "\n"
    if not text.startswith("#"):
        raise HTTPException(400, "The first line must be the chapter title, starting with #.")
    history = project / "chapters" / "history"
    history.mkdir(exist_ok=True)
    shutil.copy2(path, history / f"{path.stem}-{dt.datetime.now():%Y%m%d-%H%M%S}.txt")
    path.write_text(text, encoding="utf-8")
    SUMMARY_CACHE.pop(slug, None)
    return {"ok": True}


@app.post("/api/projects/{slug}/chapters/{file}/skip")
def chapter_skip(slug: str, file: str):
    project = project_dir(slug)
    if not CHAPTER_RE.match(file) or not (project / "chapters" / file).exists():
        raise HTTPException(404, "No such chapter.")
    (project / "chapters" / "skipped").mkdir(exist_ok=True)
    shutil.move(str(project / "chapters" / file), str(project / "chapters" / "skipped" / file))
    SUMMARY_CACHE.pop(slug, None)
    return {"ok": True}


@app.post("/api/projects/{slug}/chapters/{file}/restore")
def chapter_restore(slug: str, file: str):
    project = project_dir(slug)
    src = project / "chapters" / "skipped" / file
    if not CHAPTER_RE.match(file) or not src.exists():
        raise HTTPException(404, "No such chapter.")
    if (project / "chapters" / file).exists():
        raise HTTPException(409, "A chapter with that number already exists.")
    shutil.move(str(src), str(project / "chapters" / file))
    SUMMARY_CACHE.pop(slug, None)
    return {"ok": True}


@app.post("/api/projects/{slug}/render")
def project_render(slug: str):
    return enqueue_render(slug, "render", label=None).to_dict()


@app.post("/api/projects/{slug}/preview")
def project_preview(slug: str, body: ChapterNo):
    return enqueue_render(slug, "preview", ["--chapter", str(body.chapter)],
                          extra={"chapter": body.chapter}).to_dict()


@app.post("/api/projects/{slug}/redo")
def project_redo(slug: str, body: Ids):
    ids = [i for i in body.ids if re.fullmatch(r"\d{2,4}-\d{3,5}", i)]
    if not ids:
        raise HTTPException(400, "No valid chunk IDs.")
    return enqueue_render(slug, "redo", ids, extra={"ids": ids}).to_dict()


# --- quick speech


@app.post("/api/say")
def say(body: SayRequest):
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Type something to hear.")
    if len(text) > 20000:
        raise HTTPException(400, "That's long for a quick listen; create an audiobook from it instead.")
    out = SAY_DIR / f"{dt.datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}.mp3"
    args = ["say", text, "--out", str(out)]
    if body.voice:
        voice_exists(body.voice)
        args += ["--voice", body.voice]
    if body.temperature is not None:
        args += ["--temperature", str(body.temperature)]
    if body.project and SLUG_RE.match(body.project):
        args += ["--project", body.project]
    label = body.label or (text[:48] + ("…" if len(text) > 48 else ""))
    return QUEUE.add(Job("say", args, label, extra={"voice": body.voice})).to_dict()


# --- voices


def voice_exists(name: str):
    if name.startswith("preset:"):
        if name.split(":", 1)[1] not in PRESETS:
            raise HTTPException(400, "Unknown built-in speaker.")
        return
    try:
        load_voice(name, VOICES)
    except FileNotFoundError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/voices")
def voices():
    default = P.load_settings()["voice"]
    out = []
    for vf in sorted(VOICES.glob("*/voice.yaml")):
        try:
            v = load_voice(vf.parent.name, VOICES)
        except Exception:  # noqa: BLE001
            continue
        ref = Path(v["files"].get("24k_mono", ""))
        out.append({
            "id": vf.parent.name, "name": vf.parent.name, "description": v.get("description") or "",
            "seconds": v.get("seconds"), "transcript": v.get("transcript"), "kind": "designed" if v.get("origin") else "clone",
            "sample": media_url(ref) if ref.exists() else None, "default": vf.parent.name == default,
            "matched": bool(v.get("delivery")),
        })
    for name, desc in PRESETS.items():
        vid = f"preset:{name}"
        out.append({"id": vid, "name": name, "description": desc, "kind": "preset", "sample": None,
                    "default": vid == default})
    return {"voices": out, "default": default}


@app.post("/api/voices")
def voice_add(file: Annotated[UploadFile, File()], name: Annotated[str, Form()],
              transcript: Annotated[str, Form()] = "", description: Annotated[str, Form()] = ""):
    slug = P.slugify(name)
    if not slug or (VOICES / slug).exists():
        raise HTTPException(400, f"A voice called '{slug}' already exists; pick another name.")
    fname = safe_name(file.filename or "clip.wav")
    if Path(fname).suffix.lower() not in AUDIO_TYPES:
        raise HTTPException(400, "Please choose an audio file (WAV, MP3, M4A, AIFF or FLAC).")
    staging = UPLOADS / "voices"
    staging.mkdir(parents=True, exist_ok=True)
    src = staging / f"{dt.datetime.now():%Y%m%d-%H%M%S}-{fname}"
    with src.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    try:
        info = prepare_voice(src, slug, transcript.strip() or None, VOICES)
    except Exception as exc:  # noqa: BLE001
        shutil.rmtree(VOICES / slug, ignore_errors=True)
        raise HTTPException(400, f"Couldn't read that audio file: {exc}") from exc
    if description.strip():
        vf = VOICES / slug / "voice.yaml"
        data = yaml.safe_load(vf.read_text())
        data["description"] = description.strip()
        vf.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return {"id": slug, "seconds": info["seconds"], "warnings": info["warnings"]}


@app.post("/api/voices/default")
def voice_default(body: Settings):
    if not body.voice:
        raise HTTPException(400, "Choose a voice.")
    voice_exists(body.voice)
    set_config_value("voice", body.voice)
    return {"default": body.voice}


# --- pronunciations


@app.get("/api/pronunciations")
def pron_get():
    data = yaml.safe_load(PRON.read_text()) if PRON.exists() else {}
    return {"entries": [{"word": str(k), "say": str(v)} for k, v in (data or {}).items()]}


@app.put("/api/pronunciations")
def pron_put(body: Pron):
    header = []
    if PRON.exists():
        for line in PRON.read_text().splitlines():
            if line.startswith("#") or not line.strip():
                header.append(line)
            else:
                break
    entries = {}
    for e in body.entries:
        word, say_as = str(e.get("word", "")).strip(), str(e.get("say", "")).strip()
        if word and say_as:
            entries[word] = say_as
    body_text = yaml.safe_dump(entries, sort_keys=False, allow_unicode=True) if entries else ""
    text = "\n".join(header).rstrip() + "\n\n" + body_text
    yaml.safe_load(text)
    if PRON.exists():
        hist = ROOT / "logs" / "pronunciations-history"
        hist.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PRON, hist / f"pronunciations-{dt.datetime.now():%Y%m%d-%H%M%S}.yaml")
    PRON.write_text(text)
    SUMMARY_CACHE.clear()
    return pron_get()


# --- settings


@app.get("/api/settings")
def settings_get():
    s = P.load_settings()
    return {
        "voice": s["voice"], "temperature": s["sampling"]["temperature"],
        "sentence": s["pauses"]["sentence"], "paragraph": s["pauses"]["paragraph"],
        "after_title": s["pauses"]["after_title"], "speak_titles": s.get("speak_titles", True),
        "wer_threshold": s["qa"]["wer_threshold"], "max_retries": s["qa"]["max_retries"],
        "model": s["model"], "system": system_info(),
    }


@app.put("/api/settings")
def settings_put(body: Settings):
    limits = {"temperature": (0.3, 1.3), "sentence": (0.0, 2.0), "paragraph": (0.0, 4.0),
              "after_title": (0.0, 6.0), "wer_threshold": (0.01, 0.5), "max_retries": (0, 6)}
    for key, value in body.model_dump(exclude_none=True).items():
        if key == "voice":
            voice_exists(value)
        elif key in limits:
            lo, hi = limits[key]
            value = max(lo, min(hi, value))
            value = int(value) if key == "max_retries" else round(float(value), 3)
        set_config_value(key, value)
    SUMMARY_CACHE.clear()
    return settings_get()


def system_info() -> dict:
    def sysctl(name):
        return subprocess.run(["sysctl", "-n", name], capture_output=True, text=True).stdout.strip()

    usage = shutil.disk_usage(str(ROOT))
    mem = subprocess.run(["memory_pressure", "-Q"], capture_output=True, text=True).stdout
    m = re.search(r"free percentage:\s*(\d+)%", mem)
    import importlib.metadata as md

    return {
        "chip": sysctl("machdep.cpu.brand_string"), "memory_gb": round(int(sysctl("hw.memsize") or 0) / 2**30),
        "memory_free_pct": int(m.group(1)) if m else None, "disk_free_gb": round(usage.free / 1e9),
        "mlx_audio": md.version("mlx-audio"), "folder": str(Path.home() / "AudiobookTTS"),
    }


@app.post("/api/reveal-root")
def reveal_root():
    subprocess.run(["open", str(ROOT)], check=False)
    return {"ok": True}


# --- static files

app.mount("/media/projects", StaticFiles(directory=str(PROJECTS), check_dir=False), name="projects")
app.mount("/media/voices", StaticFiles(directory=str(VOICES)), name="voices")
app.mount("/media/say", StaticFiles(directory=str(SAY_DIR), check_dir=False), name="say")
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


@app.get("/")
def index():
    # Stamp asset URLs with their modification time so an updated app.js/app.css is never stale.
    html = (STATIC / "index.html").read_text()
    for name in ("app.css", "app.js"):
        html = html.replace(f"/static/{name}", f"/static/{name}?v={int((STATIC / name).stat().st_mtime)}")
    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})


def main(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True):
    import uvicorn

    for d in (PROJECTS, SAY_DIR):
        d.mkdir(parents=True, exist_ok=True)
    url = f"http://{host}:{port}/"
    if open_browser:
        threading.Timer(1.2, lambda: subprocess.run(["open", url], check=False)).start()
    print(f"Audiobook Studio is running at {url}  (press Control-C to stop)", flush=True)
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
