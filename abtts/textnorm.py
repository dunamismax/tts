"""English text normalization for narration: spell out what TTS models misread.

Testing (docs/ab-test.md) showed Qwen3 preset and voice-design models misread years
("1919" -> "one hundred and ninety-nine") and currency ("£250"). Everything here turns
digits and abbreviations into the words a narrator would say.
"""

from __future__ import annotations

import re

from num2words import num2words

MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December|"
    "Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)
_MONTH_FULL = {
    "jan": "January", "feb": "February", "mar": "March", "apr": "April", "jun": "June",
    "jul": "July", "aug": "August", "sep": "September", "sept": "September", "oct": "October",
    "nov": "November", "dec": "December",
}

ABBREVIATIONS = {
    r"\bMr\.": "Mister",
    r"\bMrs\.": "Missus",
    r"\bMs\.": "Miz",
    r"\bDr\.(?=\s+[A-Z])": "Doctor",
    r"\bProf\.(?=\s+[A-Z])": "Professor",
    r"\bRev\.(?=\s+[A-Z])": "Reverend",
    r"\bCapt\.(?=\s+[A-Z])": "Captain",
    r"\bCol\.(?=\s+[A-Z])": "Colonel",
    r"\bGen\.(?=\s+[A-Z])": "General",
    r"\bLt\.(?=\s+[A-Z])": "Lieutenant",
    r"\bSgt\.(?=\s+[A-Z])": "Sergeant",
    r"\bSt\.(?=\s+[A-Z][a-z])": "Saint",
    r"\bMt\.(?=\s+[A-Z])": "Mount",
    r"\bJr\.": "Junior",
    r"\bSr\.": "Senior",
    r"\be\.g\.,?": "for example,",
    r"\bi\.e\.,?": "that is,",
    r"\betc\.": "et cetera.",
    r"\bvs\.?(?=\s)": "versus",
    r"\bNo\.(?=\s*\d)": "number",
    r"\bapprox\.": "approximately",
}

_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman_to_int(s: str) -> int | None:
    s = s.upper()
    if not s or any(c not in _ROMAN for c in s):
        return None
    total = 0
    for i, c in enumerate(s):
        v = _ROMAN[c]
        total += -v if i + 1 < len(s) and _ROMAN[s[i + 1]] > v else v
    return total


def _cardinal(n: str | int | float, american: bool) -> str:
    words = num2words(n).replace(",", "")
    if american:
        words = re.sub(r"\band\b ?", "", words).replace("  ", " ").strip()
    return words


def _year(y: int, american: bool) -> str:
    if 2000 <= y <= 2009:
        return _cardinal(y, american)
    return num2words(y, to="year")


def _ordinal(n: int) -> str:
    return num2words(n, to="ordinal")


def normalize_quotes_dashes(text: str) -> str:
    text = text.replace("‘", "'").replace("’", "'").replace("‚", "'")
    text = text.replace("“", '"').replace("”", '"').replace("„", '"')
    text = text.replace("«", '"').replace("»", '"')
    text = re.sub(r"\s*(?:--|—|―)\s*", " — ", text)  # em dash with spaces
    text = re.sub(r"(?<=\d)–(?=\d)", " to ", text)  # 1914–1918
    text = text.replace("–", " — ")
    text = re.sub(r"\.{3,}|…", "…", text)
    text = text.replace(" ", " ")
    return re.sub(r"[ \t]+", " ", text)


def expand_numbers(text: str, american: bool = True) -> str:
    # Dates first, so their numbers are read as ordinals and years.
    def dmy(m):
        day, month, year = int(m.group(1)), _MONTH_FULL.get(m.group(2).lower().rstrip("."), m.group(2)), m.group(3)
        out = f"the {_ordinal(day)} of {month}"
        return out + (f" {_year(int(year), american)}" if year else "")

    text = re.sub(
        rf"\b(?:the\s+)?(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({MONTHS})\.?(?:,?\s+(\d{{4}}))?\b", dmy, text
    )

    def mdy(m):
        month, day, year = _MONTH_FULL.get(m.group(1).lower().rstrip("."), m.group(1)), int(m.group(2)), m.group(3)
        out = f"{month} {_ordinal(day)}"
        return out + (f", {_year(int(year), american)}" if year else "")

    text = re.sub(rf"\b({MONTHS})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,\s*(\d{{4}}))?\b", mdy, text)
    text = re.sub(rf"\b({MONTHS})\s+(\d{{4}})\b", lambda m: f"{m.group(1)} {_year(int(m.group(2)), american)}", text)

    # Times: 7:45, 11:58 p.m., 9 a.m.
    def time(m):
        h, mnt, ampm = int(m.group(1)), m.group(2), m.group(3)
        words = _cardinal(h, american)
        if mnt and int(mnt):
            words += " oh " + _cardinal(int(mnt), american) if mnt.startswith("0") else " " + _cardinal(int(mnt), american)
        elif mnt:
            words += " o'clock" if not ampm else ""
        if ampm:
            words += " " + ampm[0].upper() + "M"
        return words

    text = re.sub(r"\b(\d{1,2}):(\d{2})(?:\s*([ap])\.?\s?m\.?)?(?=\W|$)", time, text, flags=re.I)
    text = re.sub(r"\b(\d{1,2})()\s*([ap])\.?\s?m\.?(?=\W|$)", time, text, flags=re.I)

    # Currency
    def money(symbol_major, symbol_minor):
        def f(m):
            raw = m.group(1).replace(",", "")
            if "." in raw:
                major, minor = raw.split(".", 1)
                minor = (minor + "0")[:2]
                out = f"{_cardinal(int(major), american)} {symbol_major}"
                return out + (f" and {_cardinal(int(minor), american)} {symbol_minor}" if int(minor) else "")
            n = int(raw)
            unit = symbol_major if n != 1 else symbol_major.rstrip("s")
            return f"{_cardinal(n, american)} {unit}"
        return f

    text = re.sub(r"£\s?([\d,]+(?:\.\d{1,2})?)", money("pounds", "pence"), text)
    text = re.sub(r"\$\s?([\d,]+(?:\.\d{1,2})?)", money("dollars", "cents"), text)
    text = re.sub(r"€\s?([\d,]+(?:\.\d{1,2})?)", money("euros", "cents"), text)

    text = re.sub(r"\b(\d+(?:\.\d+)?)\s?%", lambda m: f"{_cardinal(m.group(1) if '.' in m.group(1) else int(m.group(1)), american)} percent", text)
    text = re.sub(r"\b(\d+)(?:st|nd|rd|th)\b", lambda m: _ordinal(int(m.group(1))), text)
    text = re.sub(r"\b(1\d{3}|20\d{2})s\b", lambda m: _year(int(m.group(1)), american).replace("ty", "ties").replace("hundred", "hundreds") if m.group(1)[2:] == "00" or m.group(1)[3] == "0" else _year(int(m.group(1)), american) + "s", text)

    # Bare four-digit numbers without a thousands comma read as years (1100-2099),
    # unless followed by a unit-like word that marks a quantity.
    quantity = r"(?!\s+(?:pounds|dollars|euros|miles|feet|men|people|soldiers|copies|tons|yards|metres|meters|acres|years|kilometres|kilometers))"
    text = re.sub(rf"\b(1[1-9]\d\d|20\d\d)\b{quantity}", lambda m: _year(int(m.group(1)), american), text)

    text = re.sub(r"\b(\d{1,3}(?:,\d{3})+|\d+)\.(\d+)\b",
                  lambda m: f"{_cardinal(int(m.group(1).replace(',', '')), american)} point {' '.join(num2words(int(d)) for d in m.group(2))}", text)
    text = re.sub(r"\b\d{1,3}(?:,\d{3})+\b", lambda m: _cardinal(int(m.group(0).replace(",", "")), american), text)
    text = re.sub(r"\b\d+\b", lambda m: _cardinal(int(m.group(0)), american), text)
    # "24-inch" -> "twenty-four-inch" reads fine; collapse doubled spaces.
    return re.sub(r"[ \t]{2,}", " ", text)


def soften_caps(text: str) -> str:
    """ALL-CAPS words of 5+ letters read as shouting or get spelled out; acronyms are shorter."""
    if text.isupper() and len(text) > 12:
        return text[0] + text[1:].lower()
    # Runs of two or more capitalized words are shouted phrases: read them normally.
    text = re.sub(r"\b[A-Z][A-Z']+(?:\s+[A-Z][A-Z']+)+\b",
                  lambda m: m.group(0).lower() if any(len(w) >= 3 for w in m.group(0).split()) else m.group(0), text)
    return re.sub(r"\b[A-Z]{5,}\b", lambda m: m.group(0).capitalize(), text)


def expand_abbreviations(text: str) -> str:
    for pattern, repl in ABBREVIATIONS.items():
        text = re.sub(pattern, repl, text)
    return text


def apply_pronunciations(text: str, pronunciations: dict[str, str]) -> str:
    """Replace whole words (case-sensitive first, then case-insensitive) with respellings."""
    for word in sorted(pronunciations, key=len, reverse=True):
        say = pronunciations[word]
        text = re.sub(rf"(?<![\w-]){re.escape(word)}(?![\w-])", say, text)
    return text


def normalize_for_tts(text: str, *, numbers: bool = True, abbreviations: bool = True,
                      american: bool = True, pronunciations: dict[str, str] | None = None) -> str:
    text = soften_caps(normalize_quotes_dashes(text))
    if pronunciations:
        text = apply_pronunciations(text, pronunciations)
    if abbreviations:
        text = expand_abbreviations(text)
    if numbers:
        text = expand_numbers(text, american=american)
    return text.strip()
