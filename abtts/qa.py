"""Speech-to-text quality checks: transcribe audio and score word error rate."""

from __future__ import annotations

import re
import unicodedata

import jiwer
from num2words import num2words

STT_REPO = "mlx-community/whisper-large-v3-turbo-asr-fp16"

_ORDINAL_RE = re.compile(r"\b(\d+)(st|nd|rd|th)\b", re.I)
_YEAR_RE = re.compile(r"\b(1[1-9]\d\d|20\d\d)\b")
_NUM_RE = re.compile(r"\b\d+(?:\.\d+)?\b")

# Spellings that Whisper and books disagree on but that sound identical.
_EQUIVALENTS = {
    "ok": "okay",
    "mr": "mister",
    "mrs": "missus",
    "dr": "doctor",
    "st": "saint",
    "harbor": "harbour",
    "gray": "grey",
    "color": "colour",
}


_TIME_RE = re.compile(r"\b(\d{1,2})[:.](\d{2})\s*([ap])\.?\s?m\b\.?|\b(\d{1,2})[:.](\d{2})\b", re.I)
_MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december"
# "the 14th of March", "14th March", "March 14th" and "14 March" all count as the same words.
_DATE_RE = re.compile(rf"\b(?:the\s+)?(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MONTHS})\b", re.I)
_DATE_US_RE = re.compile(rf"\b({_MONTHS})\s+(?:the\s+)?(\d{{1,2}})(?:st|nd|rd|th)?\b", re.I)


def _time_words(m: re.Match) -> str:
    hour, minute, ampm = (m.group(1), m.group(2), m.group(3)) if m.group(1) else (m.group(4), m.group(5), None)
    words = f"{num2words(int(hour))} {num2words(int(minute)) if int(minute) else ''}".strip()
    return f"{words} {ampm.lower()}m" if ampm else words


def _expand_numbers(text: str) -> str:
    text = _DATE_RE.sub(lambda m: f"{m.group(2)} {num2words(int(m.group(1)))}", text)
    text = _DATE_US_RE.sub(lambda m: f"{m.group(1)} {num2words(int(m.group(2)))}", text)
    text = _TIME_RE.sub(_time_words, text)
    text = re.sub(r"(\d),(\d{3})\b", r"\1\2", text)
    text = _ORDINAL_RE.sub(lambda m: num2words(int(m.group(1)), to="ordinal"), text)
    text = _YEAR_RE.sub(lambda m: num2words(int(m.group(1)), to="year"), text)
    return _NUM_RE.sub(lambda m: num2words(float(m.group(0)) if "." in m.group(0) else int(m.group(0))), text)


def normalize_for_wer(text: str) -> str:
    """Make reference and transcript comparable: numbers to words, no punctuation."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\[pause [\d.]+s\]", " ", text)
    text = re.sub(r"/[^/]+/", " ", text)  # inline IPA cannot be compared
    text = re.sub(r"£\s?([\d.,]+)", r"\1 pounds", text)
    text = re.sub(r"\$\s?([\d.,]+)", r"\1 dollars", text)
    text = text.replace("%", " percent")
    text = _expand_numbers(text)
    text = text.lower()
    # Hyphenated compounds are written inconsistently (south-west / southwest); join them.
    text = re.sub(r"(?<=\w)[‐‑\-](?=\w)", "", text)
    text = re.sub(r"[‐-―\-]", " ", text)
    text = re.sub(r"['’]s\b", "s", text)
    text = re.sub(r"\b([ap])\.\s?m\.", r"\1m", text)
    text = re.sub(r"[^\w\s]", " ", text)
    words = [_EQUIVALENTS.get(w, w) for w in text.split()]
    return _join_compounds(words)


def _join_compounds(words: list[str]) -> str:
    """Treat "station master" and "stationmaster" alike by gluing known pairs.

    Applied identically to reference and transcript, so it never hides a real error.
    """
    out: list[str] = []
    for w in words:
        if out and (out[-1] + w) in _COMPOUNDS:
            out[-1] = out[-1] + w
        else:
            out.append(w)
    return " ".join(out)


# Closed compounds that speech-to-text often writes as two words (or vice versa).
_COMPOUNDS = {
    "stationmaster", "sometime", "logbook", "someone", "anyone", "everyone", "into",
    "cannot", "goodbye", "headmaster", "schoolmaster", "nobody", "somebody", "everybody",
    "anybody", "outside", "inside", "upstairs", "downstairs", "afternoon", "tonight",
    "today", "tomorrow", "lighthouse", "railway", "northeast", "northwest", "southeast",
    "southwest", "northeasterly", "southwesterly",
}


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref = normalize_for_wer(reference)
    hyp = normalize_for_wer(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return float(jiwer.wer(ref, hyp))


class Transcriber:
    def __init__(self, repo: str = STT_REPO):
        self.repo = repo
        self._model = None

    def transcribe(self, wav_path: str) -> str:
        if self._model is None:
            from mlx_audio.stt import load

            self._model = load(self.repo)
        result = self._model.generate(
            str(wav_path), language="en", condition_on_previous_text=False, temperature=0.0
        )
        return result.text.strip()

    def unload(self):
        self._model = None
