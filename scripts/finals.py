"""Render the final Qwen3-TTS voice candidates through the full production pipeline.

Usage:
  uv run python scripts/finals.py render [ID ...]   # default: all candidates
  uv run python scripts/finals.py report

Pipeline per candidate: text normalization + pronunciations.yaml, chapter title with a
1.75 s pause, paragraph chunks with 0.7 s gaps, Whisper QA with up to 3 retries, ACX
mastering (44.1 kHz mono, RMS -20 dB, peaks <= -3.5 dB, -70 dB room tone), MP3 192 kbps CBR.
Outputs: ab_test/finals/
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import yaml  # noqa: E402

from abtts.audio import acx_measure, acx_pass, ffmpeg, master_acx, silence  # noqa: E402
from abtts.chunking import chunk_paragraph  # noqa: E402
from abtts.engines import Engine, Voice  # noqa: E402
from abtts.qa import Transcriber  # noqa: E402
from abtts.render import PaceTracker, QAConfig, render_chunk, write_wav  # noqa: E402
from abtts.textnorm import normalize_for_tts  # noqa: E402
from abtts.voice import load_voice  # noqa: E402
from scripts.ab_test import PASSAGE  # noqa: E402

OUT = ROOT / "ab_test" / "finals"
VOICES = ROOT / "voices"
SEED = 20261021
TITLE = "Chapter One. Carrow Junction."
NARRATE = "Calm, warm, measured audiobook narration with natural pauses."
TITLE_PAUSE, PARAGRAPH_PAUSE, SENTENCE_PAUSE = 1.75, 0.7, 0.35
MAX_CHARS = 500

CANDIDATES = {
    "F1": dict(label="designmale_t0.9", model="qwen3", voice="designmale", temperature=0.9,
               note="Your favourite 3a, through the full pipeline"),
    "F2": dict(label="designmale_t0.7", model="qwen3", voice="designmale", temperature=0.7,
               note="Your favourite 3b, through the full pipeline"),
    "F3": dict(label="designmale_t0.8", model="qwen3", voice="designmale", temperature=0.8,
               note="Same voice, middle setting; lowest error rate in tuning"),
    "F4": dict(label="deepbaritone_t0.8", model="qwen3", voice="deepbaritone", temperature=0.8,
               note="New: deep, warm baritone, sixties, American"),
    "F5": dict(label="britishmale_t0.8", model="qwen3", voice="britishmale", temperature=0.8,
               note="New: refined British RP male, fifties"),
    "F6": dict(label="warmfemale_t0.8", model="qwen3", voice="warmfemale", temperature=0.8,
               note="New: warm, mature female, forties, American"),
    "F7": dict(label="preset-Ryan_narration", model="qwen3-custom", speaker="Ryan", temperature=0.9,
               instruct=NARRATE, note="Qwen3 built-in speaker Ryan with a narration-style instruction"),
    "F8": dict(label="preset-Aiden_narration", model="qwen3-custom", speaker="Aiden", temperature=0.9,
               instruct=NARRATE, note="Qwen3 built-in speaker Aiden with a narration-style instruction"),
}


def load_pronunciations() -> dict:
    path = ROOT / "pronunciations.yaml"
    return (yaml.safe_load(path.read_text()) or {}) if path.exists() else {}


def render(cid: str, engine: Engine, stt: Transcriber, pron: dict):
    spec = CANDIDATES[cid]
    if spec.get("voice"):
        info = load_voice(spec["voice"], VOICES)
        engine.voice = Voice(ref_audio=info["files"]["24k_mono"], ref_text=info["transcript"])
    else:
        engine.voice = Voice(speaker=spec["speaker"], instruct=spec.get("instruct"))
    engine.sampling = {**engine.sampling, "temperature": spec["temperature"]}

    qa, pace = QAConfig(), PaceTracker()
    plan = [(normalize_for_tts(TITLE, pronunciations=pron), TITLE, TITLE_PAUSE)]
    for para in PASSAGE:
        chunks = chunk_paragraph(normalize_for_tts(para, pronunciations=pron), MAX_CHARS)
        original = normalize_for_tts(para)
        for i, c in enumerate(chunks):
            plan.append((c, original if len(chunks) == 1 else c, PARAGRAPH_PAUSE if i == len(chunks) - 1 else SENTENCE_PAUSE))

    pieces, chunk_log, gen_s, sr = [], [], 0.0, 24000
    for n, (text, original, pause) in enumerate(plan):
        best, takes = render_chunk(engine, text, seed=SEED + n, stt=stt, qa=qa, pace=pace,
                                   alt_references=[original])
        sr = best.sample_rate
        gen_s += sum(t.gen_seconds for t in takes)
        pieces += [best.audio, silence(pause, sr)]
        chunk_log.append({"chunk": n, "text": text, "attempts": len(takes), "wer": round(best.wer, 3),
                          "seconds": round(best.seconds, 2), "problems": best.problems})
        print(f"  {cid} chunk {n}: {best.seconds:.1f}s, WER {best.wer:.1%}, attempts {len(takes)} {best.problems or ''}", flush=True)

    raw = np.concatenate(pieces[:-1])
    stem = f"{cid}_{spec['label']}"
    raw_wav = OUT / "raw" / f"{stem}.wav"
    write_wav(raw_wav, raw, sr)
    wav = OUT / f"{stem}.wav"
    measured = master_acx(raw_wav, wav, head_s=0.75, tail_s=2.0)
    mp3 = OUT / f"{stem}.mp3"
    ffmpeg("-i", str(wav), "-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100", "-ac", "1", str(mp3))
    speech_s = len(raw) / sr
    meta = {
        "id": cid, **spec, "seed": SEED, "file": wav.name, "mp3": mp3.name,
        "audio_seconds": round(speech_s, 1), "generation_seconds": round(gen_s, 1),
        "rtf_with_qa": round(gen_s / speech_s, 3), "acx": measured, "acx_pass": acx_pass(measured),
        "mp3_acx": acx_measure(mp3), "chunks": chunk_log,
    }
    (OUT / f"{stem}.json").write_text(json.dumps(meta, indent=2))
    print(f"{stem}: {speech_s:.0f}s, RTF incl. QA {meta['rtf_with_qa']}, ACX {'PASS' if meta['acx_pass'] else 'FAIL'}", flush=True)


def render_all(ids: list[str]):
    OUT.mkdir(parents=True, exist_ok=True)
    pron = load_pronunciations()
    stt = Transcriber()
    by_model: dict[str, list[str]] = {}
    for cid in ids:
        by_model.setdefault(CANDIDATES[cid]["model"], []).append(cid)
    for model, cids in by_model.items():
        engine = Engine(model)
        for cid in cids:
            render(cid, engine, stt, pron)
        engine.unload()


def report():
    rows = [
        "| # | File | Voice | Temp | Length | RTF (incl. QA) | 10 h book | Retried chunks | RMS | Peak | Noise floor | ACX |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for p in sorted(OUT.glob("F*.json")):
        m = json.loads(p.read_text())
        a = m["acx"]
        retried = sum(1 for c in m["chunks"] if c["attempts"] > 1)
        rows.append(
            f"| {m['id']} | {m['mp3']} | {m['note']} | {m['temperature']} | {m['audio_seconds'] / 60:.1f} min | "
            f"{m['rtf_with_qa']:.2f} | {m['rtf_with_qa'] * 10:.1f} h | {retried} | {a['rms_db']} dB | {a['peak_db']} dB | "
            f"{a['noise_floor_db']} dB | {'pass' if m['acx_pass'] else 'FAIL'} |"
        )
    text = "\n".join(rows) + "\n"
    (OUT / "FINALS.md").write_text(text)
    print(text)


if __name__ == "__main__":
    if sys.argv[1] == "render":
        render_all(sys.argv[2:] or list(CANDIDATES))
    else:
        report()
