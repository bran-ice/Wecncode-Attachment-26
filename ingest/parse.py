"""Turn a manual PDF into ordered, labelled blocks of text.

Two things make Samsung manuals tractable:

1. **Every manual carries a 3-level PDF outline.** That is authoritative section
   structure — chapter, section, subsection with page numbers — so headings are
   read rather than guessed. Font-size heuristics only fill in headings that the
   outline omits.
2. **The layout is rigidly consistent.** Body text is one size (13.6pt in recent
   manuals), headings are larger and bold, a running chapter title sits at the
   very top of the page and a page number at the very bottom.

Output is a flat list of `Block`s in reading order, each carrying the page it
came from and the section path it belongs to. Chunking (in `chunk.py`) consumes
those; nothing downstream needs to know about PDFs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from core.logging_setup import get_logger

log = get_logger(__name__)

# Fractions of page height treated as running header / footer. The first real
# content line in these manuals sits at ~8% of page height, the running header
# at ~2.4% and the page number at ~96%, so these bands are comfortably clear of
# body text.
HEADER_BAND = 0.06
FOOTER_BAND = 0.94

# A line this much larger than body text is a heading. Samsung's smallest
# heading is 16.6pt against 13.6pt body, so 1.5pt separates them safely.
HEADING_SIZE_DELTA = 1.5

BOLD_FONTS = re.compile(r"-(6|7|8|9)00$|bold", re.IGNORECASE)


@dataclass
class Block:
    """One paragraph, heading, or table from a manual."""

    text: str
    page: int  # 1-based, matches what the reader sees cited
    kind: str  # "heading" | "body" | "table"
    level: int = 0  # outline depth for headings
    section_path: str = ""

    def is_heading(self) -> bool:
        return self.kind == "heading"


@dataclass
class _Line:
    text: str
    y: float
    x: float
    size: float
    bold: bool


@dataclass
class ParsedDoc:
    path: Path
    blocks: list[Block] = field(default_factory=list)
    n_pages: int = 0
    body_size: float = 0.0
    skipped_pages: int = 0


def _normalize(text: str) -> str:
    """Collapse whitespace and repair the artefacts of PDF text extraction."""
    text = text.replace("­", "")  # soft hyphen
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"[‘’]", "'", text)
    text = re.sub(r"[“”]", '"', text)
    return re.sub(r"[ \t ]+", " ", text).strip()


def _page_lines(page, header_y: float, footer_y: float, table_boxes) -> list[_Line]:
    """Text lines in reading order, minus chrome and anything inside a table."""
    lines: list[_Line] = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            y0, x0 = line["bbox"][1], line["bbox"][0]
            if y0 < header_y or y0 > footer_y:
                continue
            if any(_inside(line["bbox"], box) for box in table_boxes):
                continue
            text = _normalize("".join(s["text"] for s in spans))
            if not text:
                continue
            # The span carrying the most characters, not the largest one: body
            # lines frequently embed an oversized icon glyph or a step numeral,
            # and taking the max size promotes ordinary prose to a heading.
            dominant = max(spans, key=lambda s: len(s["text"].strip()))
            lines.append(
                _Line(
                    text=text,
                    y=y0,
                    x=x0,
                    size=round(dominant["size"], 1),
                    bold=bool(BOLD_FONTS.search(dominant["font"])),
                )
            )
    lines.sort(key=lambda l: (round(l.y, 1), l.x))
    return lines


def _join_wrapped(lines: list[_Line], body_size: float) -> list[_Line]:
    """Rejoin a heading that wraps onto a second line.

    PDF extraction yields one `_Line` per visual line, so a long heading arrives
    split. Left alone the first half becomes the section title — truncated
    mid-sentence — and the second half opens a bogus section of its own
    ("...be covered by the warranty service"). Section paths are printed under
    every citation, so a fragment is a visible defect.
    """
    out: list[_Line] = []
    for line in lines:
        previous = out[-1] if out else None
        is_big = line.size >= body_size + HEADING_SIZE_DELTA or (
            line.bold and line.size > body_size
        )
        if (
            previous
            and is_big
            and previous.size == line.size
            and previous.bold == line.bold
            and 0 <= line.y - previous.y <= line.size * 1.8
            and not previous.text.rstrip().endswith((".", "!", "?"))
        ):
            previous.text = _normalize(f"{previous.text} {line.text}")
            continue
        out.append(line)
    return out


def _inside(bbox, box) -> bool:
    """True when a text line falls within a detected table's area."""
    x0, y0, x1, y1 = bbox
    bx0, by0, bx1, by1 = box
    return x0 >= bx0 - 2 and x1 <= bx1 + 2 and y0 >= by0 - 2 and y1 <= by1 + 2


def _body_size(doc, sample_pages: Iterable[int]) -> float:
    """The dominant font size, measured by characters not by line count.

    Counting characters matters: a page can carry more heading *lines* than body
    lines while body text still dominates the actual content.
    """
    volume: dict[float, int] = {}
    for index in sample_pages:
        for block in doc[index].get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if stripped := span["text"].strip():
                        size = round(span["size"], 1)
                        volume[size] = volume.get(size, 0) + len(stripped)
    return max(volume, key=volume.get) if volume else 12.0


def _table_markdown(table) -> str:
    """Serialize a detected table as markdown.

    Tables in these manuals are reference material — button functions, status
    icons, specifications — the exact content a spec question asks for. Flattened
    to prose the row/column pairing is lost, so it is kept as markdown.
    """
    rows = [
        [_normalize(cell or "").replace("\n", " ") for cell in row]
        for row in table.extract()
    ]
    rows = [r for r in rows if any(cell for cell in r)]
    if len(rows) < 2:
        return ""

    header, *body = rows
    width = len(header)
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * width]
    for row in body:
        row = (row + [""] * width)[:width]
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


class _SectionTracker:
    """Maintains the current chapter > section > subsection path.

    Driven by the PDF outline, which gives each heading's title, depth and page.
    A page can start mid-section and contain several headings, so the tracker
    advances when it actually sees a heading's text on the page rather than
    assuming one section per page.
    """

    def __init__(self, toc: list[list]):
        self.pending: dict[int, list[tuple[int, str]]] = {}
        # Each outline entry's full ancestry, resolved from the outline itself.
        # A chapter title that is only ever drawn as a running header — which we
        # strip — would otherwise never enter the stack, and every section under
        # it would silently lose its chapter.
        self.ancestry: dict[tuple[int, str], list[str]] = {}
        walk: list[str] = []
        for level, title, page in toc:
            title = _normalize(title)
            del walk[level - 1 :]
            while len(walk) < level - 1:
                walk.append("")
            walk.append(title)
            self.pending.setdefault(page, []).append((level, title))
            self.ancestry[(level, title.lower())] = list(walk)
        self.stack: list[str] = []

    def titles_on(self, page: int) -> list[tuple[int, str]]:
        return self.pending.get(page, [])

    def enter(self, level: int, title: str) -> None:
        if known := self.ancestry.get((level, title.lower())):
            self.stack = list(known)
            return
        del self.stack[level - 1 :]
        while len(self.stack) < level - 1:
            self.stack.append("")
        self.stack.append(title)

    def path(self) -> str:
        return " > ".join(part for part in self.stack if part)


def parse_pdf(path: str | Path, max_pages: Optional[int] = None) -> ParsedDoc:
    """Parse one manual into blocks. Pure function of the file — no I/O beyond it."""
    import pymupdf

    path = Path(path)
    doc = pymupdf.open(path)
    toc = doc.get_toc()
    tracker = _SectionTracker(toc)

    # Everything before the first outline target is cover art and the manual's
    # own printed contents list, which would otherwise become chunks of
    # disconnected section titles and page numbers.
    first_content_page = min((e[2] for e in toc), default=1)

    sample = range(first_content_page, min(first_content_page + 40, doc.page_count))
    body_size = _body_size(doc, sample)

    parsed = ParsedDoc(path=path, n_pages=doc.page_count, body_size=body_size)
    parsed.skipped_pages = first_content_page - 1
    last = min(doc.page_count, max_pages or doc.page_count)

    for index in range(first_content_page - 1, last):
        page = doc[index]
        page_no = index + 1
        height = page.rect.height

        try:
            found = page.find_tables()
            tables = list(found.tables)
        except Exception as exc:  # table finding is best-effort
            log.debug("%s p.%d: table detection failed (%s)", path.name, page_no, exc)
            tables = []
        table_boxes = [t.bbox for t in tables]

        lines = _join_wrapped(
            _page_lines(page, height * HEADER_BAND, height * FOOTER_BAND, table_boxes),
            body_size,
        )
        expected = tracker.titles_on(page_no)

        paragraph: list[str] = []

        def flush() -> None:
            if paragraph:
                text = _normalize(" ".join(paragraph))
                if text:
                    parsed.blocks.append(
                        Block(text, page_no, "body", section_path=tracker.path())
                    )
                paragraph.clear()

        for line in lines:
            level = _heading_level(line, body_size, expected)
            if level:
                flush()
                title = line.text
                tracker.enter(level, title)
                parsed.blocks.append(
                    Block(title, page_no, "heading", level, tracker.path())
                )
                expected = [e for e in expected if e[1].lower() != title.lower()]
                continue
            paragraph.append(line.text)

        flush()

        for table in tables:
            if markdown := _table_markdown(table):
                parsed.blocks.append(
                    Block(markdown, page_no, "table", section_path=tracker.path())
                )

    doc.close()
    log.info(
        "%s: %d blocks from %d pages (body %.1fpt, skipped %d front-matter pages)",
        path.name,
        len(parsed.blocks),
        last - first_content_page + 1,
        body_size,
        parsed.skipped_pages,
    )
    return parsed


def _heading_level(
    line: _Line, body_size: float, expected: list[tuple[int, str]]
) -> int:
    """Return the outline depth of this line, or 0 if it is body text.

    The outline wins when it names this line: it knows the true depth, and a
    font-size rule cannot distinguish a chapter title from a subsection that
    happens to be set at the same size.
    """
    lowered = line.text.lower()
    for level, title in expected:
        if lowered == title.lower():
            return level

    # Diagram callouts ("1", "2") sit in figure-label type: large, bold, short.
    # Typography cannot tell them from a heading, but they are never words.
    if len(line.text) < 3 or not re.search(r"[A-Za-z]", line.text):
        return 0
    if _looks_like_prose(line.text):
        return 0
    if line.size >= body_size + HEADING_SIZE_DELTA:
        return 3  # unlisted heading: deeper than anything the outline names
    if line.bold and line.size > body_size and len(line.text) < 60:
        return 3
    return 0


# Numbered steps ("1 Open Settings…"), bullets and notes are set in emphasised
# type in these manuals, so typography alone would file them as headings — and a
# procedure's steps would each start a new section.
_PROSE_START = re.compile(r"^\s*(\d+[.)]?\s|[•▪◦·\-–—]\s*|Note\b|Tip\b)", re.IGNORECASE)


def _looks_like_prose(text: str) -> bool:
    if _PROSE_START.match(text):
        return True
    # Continuation lines from a wrapped heading or an interrupted sentence begin
    # mid-thought — lowercase, or on punctuation like "→Settings". An outline
    # heading is matched by title before this ever runs, so real headings that
    # break the convention are unaffected.
    stripped = text.lstrip("•▪◦·-–— \t")
    if stripped and not (stripped[0].isupper() or stripped[0].isdigit()):
        return True
    # A heading never ends in sentence punctuation; a bold lead-in like
    # "Battery." does, and would otherwise open a bogus section.
    if text.rstrip().endswith((".", ",", ":", ";")):
        return True
    return len(text) > 90
