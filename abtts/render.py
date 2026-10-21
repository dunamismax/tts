"""Render text chunks with automatic quality control.

Every chunk is transcribed with Whisper and scored against the text. A chunk is
regenerated with a new seed (up to max_retries times) when its word error rate is
above the threshold or its pace (characters per second) is far from the narrator's
normal pace, which catches skipped text, repeated text and long silences. The best
take is kept and anything still outside limits is flagged for a human to listen to.
"""

from __future__ import annotations

import statistics
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import soundfile as sf

from .engines import Engine
from .qa import Transcriber, word_error_rate

DEFAULT_CPS = 14.0  # characters per second of a typical narrator, used until we have data


@dataclass
class QAConfig:
    wer_threshold: float = 0.08
    max_retries: int = 3
    pace_low: float = 0.6  # flag if chars/sec falls below 60% of the narrator's median
    pace_high: float = 1.6  # or rises above 160% of it
    enabled: bool = True


@dataclass
class Take:
    audio: np.ndarray
    sample_rate: int
    seed: int
    transcript: str = ""
    wer: float = 0.0
    cps: float = 0.0
    gen_seconds: float = 0.0
    problems: list[str] = field(default_factory=list)

    @property
    def seconds(self) -> float:
        return len(self.audio) / self.sample_rate


class PaceTracker:
    """Running median of characters per second for this narrator."""

    def __init__(self, seed_values: list[float] | None = None):
        self.values: list[float] = list(seed_values or [])

    @property
    def median(self) -> float:
        return statistics.median(self.values) if len(self.values) >= 3 else DEFAULT_CPS

    def add(self, cps: float):
        self.values.append(cps)


def trim_edges(audio: np.ndarray, sr: int, threshold_db: float = -50.0, keep_s: float = 0.04) -> np.ndarray:
    """Remove leading/trailing near-silence so our own pauses are exact."""
    if audio.size == 0:
        return audio
    thresh = 10 ** (threshold_db / 20)
    win = max(1, int(sr * 0.01))
    env = np.sqrt(np.convolve(audio**2, np.ones(win) / win, mode="same"))
    loud = np.nonzero(env > thresh)[0]
    if loud.size == 0:
        return audio
    keep = int(keep_s * sr)
    return audio[max(0, loud[0] - keep): min(audio.size, loud[-1] + keep)]


def render_chunk(
    engine: Engine,
    text: str,
    *,
    seed: int,
    stt: Transcriber | None,
    qa: QAConfig,
    pace: PaceTracker,
    alt_references: list[str] = (),
) -> tuple[Take, list[Take]]:
    """Generate one chunk, retrying on QA failures. Returns (best take, all takes)."""
    takes: list[Take] = []
    attempts = 1 + (qa.max_retries if qa.enabled and stt else 0)
    for attempt in range(attempts):
        take_seed = seed + attempt * 7919
        t0 = time.perf_counter()
        audio, sr = engine.synth(text, seed=take_seed)
        audio = trim_edges(audio, sr)
        take = Take(audio=audio, sample_rate=sr, seed=take_seed, gen_seconds=time.perf_counter() - t0)
        take.cps = len(text) / max(take.seconds, 0.1)

        if qa.enabled and stt:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
                sf.write(tmp.name, audio, sr)
                take.transcript = stt.transcribe(tmp.name)
            # Pronunciation respellings change the words, so score against the original too.
            take.wer = min(word_error_rate(ref, take.transcript) for ref in (text, *alt_references))
            # In very short chunks (titles) one misheard word is a huge percentage; allow one.
            threshold = max(qa.wer_threshold, 1.01 / max(len(text.split()), 1))
            if take.wer > threshold:
                take.problems.append(f"WER {take.wer:.0%}")
        if take.seconds < 0.3:
            take.problems.append("no audio")
        elif len(text) >= 40:  # pace is meaningless for a few words
            ratio = take.cps / pace.median
            if ratio < qa.pace_low:
                take.problems.append(f"too slow for its text ({ratio:.2f}x normal pace): long pause or repeat?")
            elif ratio > qa.pace_high:
                take.problems.append(f"too fast for its text ({ratio:.2f}x normal pace): skipped words?")
        takes.append(take)
        if not take.problems:
            break

    best = min(takes, key=lambda t: (len(t.problems), t.wer, abs(t.cps - pace.median)))
    if not best.problems and len(text) >= 40:
        pace.add(best.cps)
    return best, takes


def write_wav(path: Path, audio: np.ndarray, sr: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio, sr, subtype="PCM_16")
