"""Read EPUB, PDF, TXT and Markdown books into cleaned chapters.

A chapter is {"title": str, "paragraphs": [str, ...]}. Cleanup removes footnote
markers, URLs, page numbers, running headers/footers, Project Gutenberg boilerplate
and illustration captions, rejoins words hyphenated across line breaks, and
normalizes quotes and dashes. Numbers are left alone here; they are expanded at
render time so the chapter files stay readable and editable.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .textnorm import normalize_quotes_dashes, roman_to_int

SKIP_TITLES = re.compile(
    r"^(contents|table of contents|index|copyright|license|the full project gutenberg|"
    r"acknowledg|also by|about the (author|publisher)|colophon|cover|title page|"
    r"list of illustrations|illustrations)",
    re.I,
)
CHAPTER_HEADING = re.compile(
    r"^(chapter|book|part|section|prologue|epilogue|preface|introduction|foreword|afterword|"
    r"interlude|appendix)\b[\s.:\-]*([0-9ivxlcdm]+|[a-z-]+)?\b.*$",
    re.I,
)
GUTENBERG_START = re.compile(r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I)
GUTENBERG_END = re.compile(r"\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG", re.I)
URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.I)
FOOTNOTE_RE = re.compile(r"\[(?:\d{1,3}|[*†‡§]|[a-z])\]|(?<=[a-z.,;:!?”\"'])[¹²³⁴⁵⁶⁷⁸⁹⁰]+|(?<=[a-z.,;:!?”\"'])\*(?=\s|$)")
ILLUSTRATION_RE = re.compile(r"\[(?:Picture|Illustration|Image)[^\]]*\]", re.I)


@dataclass
class Book:
    title: str
    author: str
    chapters: list[dict] = field(default_factory=list)
    cover: bytes | None = None
    cover_ext: str = "jpg"


# ----------------------------------------------------------------------------- cleanup


def clean_paragraph(text: str) -> str:
    text = ILLUSTRATION_RE.sub(" ", text)
    text = re.sub(r"\{\d+\}", " ", text)  # Gutenberg page markers
    text = URL_RE.sub(" ", text)
    text = FOOTNOTE_RE.sub("", text)
    text = re.sub(r"(\w)[-­]\s*\n\s*(\w)", r"\1\2", text)  # hyphen at line break
    text = text.replace("­", "")  # soft hyphens
    text = re.sub(r"_(.+?)_", r"\1", text)  # Gutenberg _italics_
    text = re.sub(r"\s+", " ", text)
    text = normalize_quotes_dashes(text).strip()
    return fix_shouted_opening(text)


def fix_shouted_opening(text: str) -> str:
    """'HIGH above the city' (small caps in print) -> 'High above the city'."""
    m = re.match(r"^([\"'(]?)((?:[A-Z][A-Z’']+\s+){0,2}[A-Z][A-Z’']+)(\b.*)$", text)
    if not m or not re.search(r"[a-z]", m.group(3)):
        return text
    words = m.group(2).split()
    fixed = " ".join(w.capitalize() if i == 0 else w.lower() for i, w in enumerate(words))
    return m.group(1) + fixed + m.group(3)


PRINTER_RE = re.compile(r"^(printed (and bound )?(by|in)\b|the end\.?$)", re.I)


def merge_shouted_lines(paras: list[str]) -> list[str]:
    """Signs and inscriptions set as short ALL-CAPS lines become one sentence.

    ['TRESPASSERS', 'WILL BE', 'PROSECUTED'] -> ['Trespassers will be prosecuted.']
    """
    out: list[str] = []
    run: list[str] = []

    def flush():
        if len(run) >= 2:
            text = " ".join(run).lower()
            out.append(text[0].upper() + text[1:].rstrip(".") + ".")
        else:
            out.extend(run)
        run.clear()

    for p in paras:
        if len(p) <= 40 and p.isupper():
            run.append(p)
        else:
            flush()
            out.append(p)
    flush()
    return out


def is_noise(p: str) -> bool:
    if not p or not re.search(r"[A-Za-z]", p):
        return True  # "* * * * *", page numbers, ornaments
    if re.fullmatch(r"(page\s*)?\d+|[ivxlcdm]+", p.strip().lower()):
        return True
    return False


def spoken_title(title: str) -> str:
    """'CHAPTER IV.' -> 'Chapter Four.'; keeps names readable for the narrator."""
    title = clean_paragraph(title).strip(" .")

    def roman(m):
        n = roman_to_int(m.group(2))
        if n is None:
            return m.group(0)
        from num2words import num2words

        return f"{m.group(1)} {num2words(n).capitalize()}"

    title = re.sub(r"\b(chapter|book|part|section)\s+([ivxlcdm]+)\b", roman, title, flags=re.I)
    if title.isupper():
        title = title.title()
    return title + "."


def drop_gutenberg_boilerplate(raw: list[dict]) -> list[dict]:
    """Remove everything before '*** START OF ... ***' and after '*** END OF ...'."""
    flat = [(ci, pi) for ci, ch in enumerate(raw) for pi, _ in enumerate(ch["paragraphs"])]
    start = next(((ci, pi) for ci, pi in flat if GUTENBERG_START.search(raw[ci]["paragraphs"][pi])
                  or re.match(r"\*\*\*\s*START OF", raw[ci]["paragraphs"][pi], re.I)), None)
    end = next(((ci, pi) for ci, pi in flat if GUTENBERG_END.search(raw[ci]["paragraphs"][pi])), None)
    out = []
    for ci, ch in enumerate(raw):
        paras = []
        for pi, p in enumerate(ch["paragraphs"]):
            if start and (ci, pi) <= start:
                continue
            if end and (ci, pi) >= end:
                continue
            paras.append(p)
        if end and ci > end[0]:
            break
        if start and ci < start[0]:
            continue
        out.append({**ch, "paragraphs": paras})
    return out


def finish_chapters(raw: list[dict]) -> list[dict]:
    raw = drop_gutenberg_boilerplate(raw)
    # Untitled text before the first heading is front matter (title page, dedication).
    if len(raw) > 1 and not raw[0]["title"] and sum(len(p) for p in raw[0]["paragraphs"]) < 2000:
        raw = raw[1:]
    chapters = []
    for ch in raw:
        paras = [clean_paragraph(p) for p in ch["paragraphs"]]
        paras = merge_shouted_lines([p for p in paras if not is_noise(p)])
        while paras and PRINTER_RE.match(paras[-1]):
            paras = paras[:-1]
        title = clean_paragraph(ch["title"] or "").strip()
        # Drop a first paragraph that just repeats the heading.
        if paras and title and paras[0].lower().strip(" .") == title.lower().strip(" ."):
            paras = paras[1:]
        if not paras or (title and SKIP_TITLES.match(title)):
            continue
        if sum(len(p) for p in paras) < 200 and not CHAPTER_HEADING.match(title or ""):
            continue  # cover wrappers, ornaments, dedications
        chapters.append({"title": title or f"Chapter {len(chapters) + 1}", "paragraphs": paras})
    return chapters


# ----------------------------------------------------------------------------- EPUB


def read_epub(path: Path) -> Book:
    import ebooklib
    from bs4 import BeautifulSoup
    from ebooklib import epub

    book = epub.read_epub(str(path), options={"ignore_ncx": False})
    title = (book.get_metadata("DC", "title") or [[path.stem]])[0][0]
    authors = [a[0] for a in book.get_metadata("DC", "creator")]
    result = Book(title=title, author=", ".join(authors) or "Unknown")

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_COVER or (
            item.get_type() == ebooklib.ITEM_IMAGE and "cover" in item.get_name().lower()
        ):
            result.cover = item.get_content()
            result.cover_ext = item.get_name().rsplit(".", 1)[-1].lower()
            break

    toc: dict[str, list[tuple[str | None, str]]] = {}

    def walk(entries):
        for e in entries:
            if isinstance(e, tuple):
                section, children = e
                walk([section])
                walk(children)
                continue
            href = getattr(e, "href", "") or ""
            name, _, anchor = href.partition("#")
            toc.setdefault(Path(name).name, []).append((anchor or None, getattr(e, "title", "")))

    walk(book.toc)

    BLOCKS = ["p", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "li", "pre", "div"]
    raw: list[dict] = []
    for idref, _ in book.spine:
        item = book.get_item_with_id(idref)
        if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        soup = BeautifulSoup(item.get_content(), "xml" if item.get_content().lstrip().startswith(b"<?xml") else "lxml")
        for tag in soup(["script", "style", "img", "svg", "figure", "figcaption"]):
            tag.decompose()
        for tag in soup.select('[epub\\:type~="noteref"], a.noteref, sup a, a[role="doc-noteref"]'):
            tag.decompose()
        for tag in soup.select('aside, [epub\\:type~="footnote"], [epub\\:type~="endnote"], '
                               '[role="doc-footnote"], [role="doc-endnotes"], span.pagenum, .pagenum'):
            tag.decompose()
        body = soup.body or soup
        anchors = {a: t for a, t in toc.get(Path(item.get_name()).name, [])}
        file_title = anchors.pop(None, None)
        current = None
        if file_title is not None or not anchors:
            current = {"title": file_title, "paragraphs": []}
            raw.append(current)
        for el in body.find_all(BLOCKS):
            if el.find(BLOCKS):
                continue  # only leaf blocks, so text is not counted twice
            ids = {el.get("id")} | {p.get("id") for p in el.parents if p.get("id")}
            ids |= {a.get("id") for a in el.find_all(id=True)}
            hit = next((anchors.pop(i) for i in list(ids) if i in anchors), None)
            if hit is not None:
                current = {"title": hit, "paragraphs": []}
                raw.append(current)
            for br in el.find_all("br"):
                br.replace_with(" ")
            text = el.get_text("").strip()
            if current is None:
                current = {"title": None, "paragraphs": []}
                raw.append(current)
            if el.name in {"h1", "h2", "h3"} and not current["title"] and not current["paragraphs"]:
                current["title"] = text
                continue
            if text:
                current["paragraphs"].append(text)
    result.chapters = finish_chapters(raw)
    return result


# ----------------------------------------------------------------------------- PDF


_WORDS: set[str] | None = None


def english_words() -> set[str]:
    """The macOS system word list (plus simple plurals), used to repair line-break hyphens."""
    global _WORDS
    if _WORDS is None:
        path = Path("/usr/share/dict/words")
        base = {w.strip().lower() for w in path.read_text().splitlines()} if path.exists() else set()
        _WORDS = base | {w + "s" for w in base} | {w + "es" for w in base}
    return _WORDS


def read_pdf(path: Path) -> Book:
    import pymupdf

    doc = pymupdf.open(str(path))
    meta = doc.metadata or {}
    result = Book(title=meta.get("title") or path.stem, author=meta.get("author") or "Unknown")

    # Collect lines with their vertical position, then drop running headers/footers:
    # lines in the top or bottom 8% of the page that repeat on many pages (digits ignored).
    pages = []
    for page in doc:
        height = page.rect.height
        lines = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = "".join(span["text"] for span in line["spans"]).strip()
                if text:
                    size = max(span["size"] for span in line["spans"])
                    lines.append({"text": text, "y": line["bbox"][1] / height, "size": size,
                                  "block": id(block)})
        pages.append(lines)

    def key(t):
        return re.sub(r"\d+", "#", t.lower()).strip()

    edge = Counter(key(l["text"]) for lines in pages for l in lines if l["y"] < 0.08 or l["y"] > 0.92)
    repeat = {k for k, n in edge.items() if n >= max(3, len(pages) * 0.3)}

    sizes = Counter(round(l["size"]) for lines in pages for l in lines)
    body_size = sizes.most_common(1)[0][0] if sizes else 11

    toc = doc.get_toc()  # [level, title, page]
    toc_starts = {}
    for level, title, page_no in toc:
        if level <= 2 and page_no >= 1:
            toc_starts.setdefault(page_no - 1, []).append(title)

    raw: list[dict] = [{"title": None, "paragraphs": []}]
    for pno, lines in enumerate(pages):
        lines = [l for l in lines
                 if key(l["text"]) not in repeat
                 and not ((l["y"] < 0.08 or l["y"] > 0.92) and re.fullmatch(r"(page\s*)?\d+|[ivxlcdm]+", l["text"].lower()))]
        pending_titles = list(toc_starts.get(pno, []))
        para, last_block = [], None
        for l in lines:
            is_heading = round(l["size"]) >= body_size + 2 and len(l["text"]) < 90
            title_hit = pending_titles and l["text"].strip().lower().rstrip(".") in {t.lower().rstrip(".") for t in pending_titles}
            if (title_hit or (not toc and (is_heading or CHAPTER_HEADING.match(l["text"])) and len(l["text"]) < 90)):
                if para:
                    raw[-1]["paragraphs"].append("\n".join(para))
                    para = []
                raw.append({"title": l["text"], "paragraphs": []})
                last_block = l["block"]
                continue
            if last_block is not None and l["block"] != last_block and para:
                raw[-1]["paragraphs"].append("\n".join(para))
                para = []
            para.append(l["text"])
            last_block = l["block"]
        if para:
            raw[-1]["paragraphs"].append("\n".join(para))
    # Words hyphenated at a line end: "beau-\ntiful" -> "beautiful", but keep real compounds
    # ("palm-\ntrees" stays "palm-trees") when the book uses the hyphenated form elsewhere.
    all_text = "\n".join(p for ch in raw for p in ch["paragraphs"])
    words = Counter(w.lower() for w in re.findall(r"[\w'’]+(?:-[\w'’]+)*", all_text))

    dictionary = english_words()

    def dehyphenate(m):
        a, b = m.group(1), m.group(2)
        joined, compound = (a + b).lower(), f"{a}-{b}".lower()
        if words.get(compound, 0) != words.get(joined, 0):  # the book itself tells us
            return f"{a}-{b}" if words.get(compound, 0) > words.get(joined, 0) else a + b
        if b[:1].isupper():
            return f"{a}-{b}"  # Sans-Souci, Anglo-Saxon
        if joined in dictionary:
            return a + b
        if a.lower() in dictionary and b.lower().strip("'’") in dictionary:
            return f"{a}-{b}"  # lady-love, palm-trees
        return a + b

    for ch in raw:
        ch["paragraphs"] = [re.sub(r"([\w'’]+)-\n([\w'’]+)", dehyphenate, p) for p in ch["paragraphs"]]
    # Paragraphs that continue across a page break: join when the first does not end a sentence.
    for ch in raw:
        merged = []
        for p in ch["paragraphs"]:
            if merged and not re.search(r"[.!?\"”’:)]$", merged[-1].strip()) and p[:1].islower():
                merged[-1] = merged[-1] + "\n" + p
            else:
                merged.append(p)
        ch["paragraphs"] = merged
    result.chapters = finish_chapters(raw)
    return result


# ----------------------------------------------------------------------------- TXT / Markdown


def strip_gutenberg(text: str) -> str:
    start = GUTENBERG_START.search(text)
    if start:
        text = text[start.end():]
    end = GUTENBERG_END.search(text)
    if end:
        text = text[:end.start()]
    return text


def read_text(path: Path) -> Book:
    raw_text = path.read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n")
    title = re.search(r"^Title:\s*(.+)$", raw_text, re.M)
    author = re.search(r"^Author:\s*(.+)$", raw_text, re.M)
    text = strip_gutenberg(raw_text)
    is_md = path.suffix.lower() in {".md", ".markdown"}
    blocks = [b for b in re.split(r"\n\s*\n", text)]

    raw: list[dict] = [{"title": None, "paragraphs": []}]
    contents_mode = False
    for block in blocks:
        stripped = block.strip()
        if not stripped:
            continue
        one_line = "\n" not in stripped
        md_heading = re.match(r"^(#{1,3})\s+(.+)$", stripped) if is_md else None
        if md_heading:
            raw.append({"title": md_heading.group(2).strip(), "paragraphs": []})
            contents_mode = SKIP_TITLES.match(md_heading.group(2).strip()) is not None
            continue
        if one_line and re.match(r"^contents\.?$", stripped, re.I):
            contents_mode = True
            raw.append({"title": "Contents", "paragraphs": []})
            continue
        indented = block.startswith("    ") or block.startswith("\t")
        heading_like = one_line and len(stripped) < 80 and not re.search(r"[,;]$", stripped) and (
            CHAPTER_HEADING.match(stripped)
            or (stripped.isupper() and len(stripped.split()) <= 8)
            or (re.fullmatch(r"[A-Z][\w’'\- ,]+\.?", stripped) and len(stripped.split()) <= 8
                and not re.search(r"[.!?]\s", stripped) and stripped[0].isupper()
                and _looks_titled(stripped))
        )
        if heading_like and not indented:
            raw.append({"title": stripped, "paragraphs": []})
            contents_mode = False
            continue
        if contents_mode and _is_toc_block(stripped):
            continue
        contents_mode = False
        if is_md:
            stripped = re.sub(r"^[>*+-]\s+", "", stripped, flags=re.M)
            stripped = re.sub(r"[*_`]{1,3}([^*_`]+)[*_`]{1,3}", r"\1", stripped)
            stripped = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", stripped)
            stripped = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", stripped)
        raw[-1]["paragraphs"].append(stripped)

    book = Book(title=(title.group(1).strip() if title else path.stem),
                author=(author.group(1).strip() if author else "Unknown"))
    book.chapters = finish_chapters(raw)
    return book


def _is_toc_block(block: str) -> bool:
    """Lines like 'The Selfish Giant      43' or 'Page' or 'Chapter IV ..... 87'."""
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    tocish = [l for l in lines if re.search(r"(\s{2,}|\.{2,}\s*)\d+$", l) or l.lower() in {"page", "contents"}
              or CHAPTER_HEADING.match(l)]
    return bool(lines) and len(tocish) >= max(1, int(len(lines) * 0.6))


def _looks_titled(s: str) -> bool:
    """'The Happy Prince.' -> True; 'He was very sad.' -> False (Title Case check)."""
    words = [w for w in re.findall(r"[A-Za-z’']+", s)]
    small = {"a", "an", "and", "the", "of", "in", "on", "to", "for", "at", "by", "or", "with"}
    caps = [w for w in words if w.lower() not in small]
    return bool(caps) and all(w[0].isupper() for w in caps)


def read_book(path: Path) -> Book:
    suffix = path.suffix.lower()
    if suffix == ".epub":
        return read_epub(path)
    if suffix == ".pdf":
        return read_pdf(path)
    if suffix in {".txt", ".md", ".markdown", ".text"}:
        return read_text(path)
    raise ValueError(f"Unsupported file type: {suffix} (use EPUB, PDF, TXT or Markdown)")
