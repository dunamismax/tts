#!/usr/bin/env python3
"""Turn a book into a narrated audiobook, locally, with Qwen3-TTS on Apple Silicon.

  ./audiobook.py make BOOK.epub                 import + narrate + master + MP3s + M4B (resumable)
  ./audiobook.py new BOOK.epub                  import only, so you can check chapters/*.txt first
  ./audiobook.py render PROJECT                 narrate (or resume) an imported book
  ./audiobook.py preview BOOK|PROJECT --chapter 3
  ./audiobook.py status PROJECT
  ./audiobook.py redo PROJECT 03-012 [04-007 ...]
  ./audiobook.py chapters BOOK                  show detected chapters without importing
  ./audiobook.py voice add CLIP.wav --name me --transcript "exact words"
  ./audiobook.py voice list

PROJECT can be the project folder, its name, or the original book file.
Settings live in config.yaml; pronunciations in pronunciations.yaml.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / ".venv" / "bin" / "python"

# Re-launch inside the project's own environment (never the system Python).
if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
    if not VENV_PY.exists():
        sys.exit(f"Environment missing. Run this once:  cd {ROOT} && uv sync --locked")
    os.execv(str(VENV_PY), [str(VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]])

import argparse  # noqa: E402
import logging  # noqa: E402
import warnings  # noqa: E402

os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
warnings.filterwarnings("ignore")
logging.getLogger("transformers").setLevel(logging.ERROR)
sys.path.insert(0, str(ROOT))

import datetime as dt  # noqa: E402

import yaml  # noqa: E402

from abtts import project as P  # noqa: E402
from abtts.books import read_book, spoken_title  # noqa: E402
from abtts.voice import prepare_voice  # noqa: E402


class Log:
    def __init__(self, project: Path | None = None):
        self.file = (project / "run.log").open("a", encoding="utf-8") if project else None

    def __call__(self, msg: str):
        print(msg, flush=True)
        if self.file:
            self.file.write(f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")
            self.file.flush()


def overrides(args) -> dict:
    o = {}
    if getattr(args, "voice", None):
        o["voice"] = args.voice
    if getattr(args, "temperature", None) is not None:
        o["sampling"] = {"temperature": args.temperature}
    if getattr(args, "no_qa", False):
        o["qa"] = {"enabled": False}
    return o


def show_chapters(project: Path, log):
    for ch in P.read_chapters(project):
        words = sum(len(p.split()) for p in ch["paragraphs"])
        log(f"  {ch['number']:2d}. {ch['title']}  ({words:,} words, ~{words / 155:.0f} min)  chapters/{ch['file']}")


def run_pipeline(project: Path, args, chapters: list[int] | None = None, preview: bool = False):
    log = Log(project)
    settings = P.load_settings(project, overrides(args))
    meta = yaml.safe_load((project / "book.yaml").read_text())
    log(f"=== {meta['title']} by {meta['author']} | voice {settings['voice']} | "
        f"temperature {settings['sampling']['temperature']} ===")
    awake = P.keep_awake()
    try:
        plan = P.build_plan(project, settings, chapters)
        if not plan:
            log("Nothing to do: no matching chapters.")
            return
        stats = P.generate(project, plan, settings, log=log)
        out_dir = project / "output" / "preview" if preview else None
        results = P.assemble(project, plan, settings, log=log, out_dir=out_dir)
        m4b = None
        if not preview and not chapters:
            m4b = P.make_m4b(project, results, settings, log=log)
        full_plan = P.build_plan(project, settings)
        report = P.write_report(project, full_plan if not chapters else plan, results, settings, stats, m4b)
        flagged = sum(1 for c in plan if (i := P.chunk_info(project, c)) and i["problems"])
        log(f"Report: {report}")
        if preview:
            for r in results:
                if r.get("complete"):
                    log(f"Preview ready: {r['mp3']}")
        elif m4b:
            log(f"Done. Audiobook: {m4b}")
            log(f"Chapter MP3s: {project / 'output' / 'mp3'}")
        if flagged:
            log(f"{flagged} chunk(s) flagged for a listen; see the report.")
    except KeyboardInterrupt:
        log("Stopped. Everything finished so far is saved; run the same command again to resume.")
        sys.exit(130)
    finally:
        if awake:
            awake.terminate()


def cmd_new(args):
    project = P.import_book(Path(args.book), name=args.name, title=args.title, author=args.author)
    meta = yaml.safe_load((project / "book.yaml").read_text())
    log = Log(project)
    log(f"Imported '{meta['title']}' by {meta['author']} into {project}")
    show_chapters(project, log)
    log("Check the chapter text in chapters/ (edit or delete files freely), then run:")
    log(f"  ./audiobook.py render {project.name}")


def cmd_make(args):
    project, created = P.project_for(args.book, name=args.name, title=args.title, author=args.author)
    if created:
        log = Log(project)
        log(f"Imported into {project}")
        show_chapters(project, log)
    run_pipeline(project, args)


def cmd_render(args):
    project, _ = P.project_for(args.project)
    chapters = [int(x) for x in args.chapters.split(",")] if args.chapters else None
    run_pipeline(project, args, chapters)


def cmd_preview(args):
    project, created = P.project_for(args.book)
    if created:
        print(f"Imported into {project}")
        show_chapters(project, print)
    run_pipeline(project, args, [args.chapter], preview=True)


def cmd_status(args):
    project = P.find_project(args.project)
    settings = P.load_settings(project)
    plan = P.build_plan(project, settings)
    meta = yaml.safe_load((project / "book.yaml").read_text())
    infos = [P.chunk_info(project, c) for c in plan]
    done = [i for i in infos if i]
    todo_chars = sum(len(c.text) for c, i in zip(plan, infos) if not i)
    gen = sum(i["generation_seconds"] for i in done)
    chars_done = sum(len(i["text"]) for i in done)
    rate = chars_done / gen if gen else 14 / 0.9  # characters per second of compute
    print(f"{meta['title']}: {len(done)}/{len(plan)} chunks done, "
          f"{sum(1 for i in done if i['problems'])} flagged.")
    print(f"Remaining: {todo_chars:,} characters, about {P.fmt_duration(todo_chars / rate)} of rendering.")
    m4b = list((project / "output").glob("*.m4b"))
    print(f"Audiobook: {m4b[0] if m4b else 'not built yet'}")


def cmd_redo(args):
    project = P.find_project(args.project)
    settings = P.load_settings(project, overrides(args))
    chapters = set()
    for cid in args.ids:
        chunk = P.redo_chunk(project, cid, settings)
        chapters.add(chunk.chapter)
        print(f"{cid}: a new take will be generated (the old one stays in cache/).")
    run_pipeline(project, args, sorted(chapters))
    # Rebuild the full book outputs so the M4B includes the new takes.
    run_pipeline(project, args)


def cmd_chapters(args):
    book = read_book(Path(args.book))
    print(f"{book.title} by {book.author}: {len(book.chapters)} chapters")
    for n, ch in enumerate(book.chapters, 1):
        words = sum(len(p.split()) for p in ch["paragraphs"])
        print(f"  {n:2d}. {spoken_title(ch['title'])}  ({words:,} words)  starts: {ch['paragraphs'][0][:70]}...")


def cmd_voice(args):
    if args.action == "list":
        for d in sorted(P.VOICES.glob("*/voice.yaml")):
            v = yaml.safe_load(d.read_text())
            print(f"  {v['name']:16s} {v['seconds']:5.1f}s  {(v.get('transcript') or '')[:60]}")
        return
    if not args.clip or not args.name:
        sys.exit("Usage: audiobook.py voice add CLIP.wav --name NAME --transcript \"exact words\"")
    info = prepare_voice(Path(args.clip).expanduser(), args.name, args.transcript, P.VOICES)
    print(f"Voice '{args.name}' ready ({info['seconds']} s): {P.VOICES / args.name}")
    for w in info["warnings"]:
        print(f"  warning: {w}")
    print(f"Use it by setting  voice: {args.name}  in config.yaml, or pass --voice {args.name}.")


def main():
    ap = argparse.ArgumentParser(prog="audiobook.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def gen_opts(p):
        p.add_argument("--voice", help="voice name from voices/ (overrides config.yaml)")
        p.add_argument("--temperature", type=float, help="sampling temperature (overrides config.yaml)")
        p.add_argument("--no-qa", action="store_true", help="skip speech-to-text checks (faster, riskier)")

    p = sub.add_parser("new", help="import a book into a project")
    p.add_argument("book")
    for opt in ("--name", "--title", "--author"):
        p.add_argument(opt)
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("make", help="import (if needed) and narrate a whole book")
    p.add_argument("book")
    for opt in ("--name", "--title", "--author"):
        p.add_argument(opt)
    gen_opts(p)
    p.set_defaults(func=cmd_make)

    p = sub.add_parser("render", help="narrate or resume a project")
    p.add_argument("project")
    p.add_argument("--chapters", help="only these chapters, e.g. 1,2,5")
    gen_opts(p)
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("preview", help="render one chapter for a quick listen")
    p.add_argument("book")
    p.add_argument("--chapter", type=int, required=True)
    gen_opts(p)
    p.set_defaults(func=cmd_preview)

    p = sub.add_parser("status", help="show progress")
    p.add_argument("project")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("redo", help="regenerate specific chunks with a fresh take")
    p.add_argument("project")
    p.add_argument("ids", nargs="+", help="chunk IDs like 03-012 (from report.md)")
    gen_opts(p)
    p.set_defaults(func=cmd_redo)

    p = sub.add_parser("chapters", help="list chapters a book file would be split into")
    p.add_argument("book")
    p.set_defaults(func=cmd_chapters)

    p = sub.add_parser("voice", help="add or list narrator voices")
    p.add_argument("action", choices=["add", "list"])
    p.add_argument("clip", nargs="?")
    p.add_argument("--name")
    p.add_argument("--transcript")
    p.set_defaults(func=cmd_voice)

    args = ap.parse_args()
    try:
        args.func(args)
    except (FileNotFoundError, FileExistsError, KeyError, ValueError) as exc:
        sys.exit(f"Error: {exc}")


if __name__ == "__main__":
    main()
