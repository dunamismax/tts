"""Split text into TTS chunks at sentence or paragraph boundaries, never mid-sentence."""

from __future__ import annotations

import re

# Abbreviations whose trailing period does not end a sentence.
_NO_BREAK = {
    "mr", "mrs", "ms", "dr", "prof", "rev", "capt", "col", "gen", "lt", "sgt", "st", "mt",
    "jr", "sr", "vs", "etc", "no", "e.g", "i.e", "fig", "vol", "ch", "p", "pp", "a.m", "p.m",
}
_SENT_END = re.compile(r'([.!?…]+["\')\]]*)(\s+)(?=["\'(\[]?[A-Z0-9“‘])')


def split_sentences(paragraph: str) -> list[str]:
    parts: list[str] = []
    start = 0
    for m in _SENT_END.finditer(paragraph):
        before = paragraph[start:m.start(1)]
        last_word = re.split(r"\s", before)[-1].lower().strip("\"'(")
        if last_word.rstrip(".") in _NO_BREAK or re.fullmatch(r"[a-z]", last_word):
            continue
        parts.append(paragraph[start:m.end(1)].strip())
        start = m.end()
    tail = paragraph[start:].strip()
    if tail:
        parts.append(tail)
    return [p for p in parts if p]


def chunk_paragraph(paragraph: str, max_chars: int) -> list[str]:
    """Pack whole sentences into chunks of at most max_chars.

    A single sentence longer than max_chars becomes its own chunk (never cut).
    """
    paragraph = " ".join(paragraph.split())
    if len(paragraph) <= max_chars:
        return [paragraph] if paragraph else []
    chunks: list[str] = []
    current = ""
    for sentence in split_sentences(paragraph):
        candidate = f"{current} {sentence}".strip()
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return _rebalance(chunks, max_chars)


def _rebalance(chunks: list[str], max_chars: int) -> list[str]:
    """Merge a tiny trailing chunk into its neighbour when it still fits comfortably."""
    if len(chunks) >= 2 and len(chunks[-1]) < max_chars * 0.25:
        merged = f"{chunks[-2]} {chunks[-1]}"
        if len(merged) <= max_chars * 1.25:
            chunks[-2:] = [merged]
    return chunks
