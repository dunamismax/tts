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


def _expand_numbers(text: str) -> str:
    text = text.replace(",", "") if re.search(r"\d,\d{3}", text) else text
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
    text = re.sub(r"[^\w\s]", " ", text)
    words = [_EQUIVALENTS.get(w, w) for w in text.split()]
    return " ".join(words)


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
