"""Find the illustrations on a manual page and render them to PNG.

**Regions are rendered, not images extracted.** Measured on the A05 excerpts:
on the pages that carry a real figure, the embedded raster and the vector
drawings occupy the *same* bounding box — Samsung draws the callout leader
lines, the numbered labels and the mode strip as vector paths layered over a
raster screenshot. `page.get_images()` hands back the photo with none of that
annotation, which is the part that answers "where do I tap". Rendering the
region composites both, exactly as the reader sees it.

Detection is four rules, each of which exists because the simpler version
failed on this corpus:

- **`MIN_PT`** — most raster XObjects in these manuals are 6x17 to 19x11 pt:
  status-bar glyphs and key symbols inlined into prose. Taking every image
  yields a stream of 16x16 icons and no figures.
- **`PAGE_FRACTION`** — a chapter-opener page has a full-page background
  rectangle. Unioning every large path reported p.1 of the "Apps and features"
  excerpt as a single 623x870 "figure": the whole page.
- **`GAP`** — a figure arrives as many paths plus a raster. They have to be
  clustered back together or one illustration becomes a dozen slivers.
- **`MAX_WORDS_INSIDE`** — a region full of prose is page furniture (a boxed
  note, a table rule), not an illustration.

The thresholds are tuned for Samsung's layout and are the first thing to
revisit if a different publisher's manual is ever ingested.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from core.logging_setup import get_logger

if TYPE_CHECKING:  # pymupdf is imported lazily, as in ingest/parse.py
    import pymupdf

log = get_logger(__name__)

# Smaller than this on either side and it is an inline icon, not a figure.
MIN_PT = 60.0
# A path covering this much of the page is a background panel.
PAGE_FRACTION = 0.5
# Boxes nearer than this belong to one illustration.
GAP = 20.0
# More words than this wholly inside the box and it is not an illustration.
MAX_WORDS_INSIDE = 25

# 150 DPI renders the 113x237pt phone diagrams at ~235x494 px — sharp in a
# Streamlit column without carrying full-page-scan weight.
RENDER_DPI = 150

FIGURE_DIR = "figures"


@dataclass
class DetectedFigure:
    """A figure found on a page, before it has been rendered or stored."""

    page: int  # 1-based
    bbox: tuple[float, float, float, float]
    # Where the figure sits vertically on the page. Reading-order association
    # in `ingest/chunk.py` needs this to place the figure among the text blocks.
    top: float


@dataclass
class RenderedFigure:
    """A figure written to disk, before it is tied to a doc_id and a chunk."""

    page: int
    filename: str
    width: int
    height: int


def figure_out_dir(store_root: Path, doc_id: str) -> Path:
    """Where one document's figures are written.

    Inside the store root, so `staging_store()` swaps images, database and
    index together — images written anywhere else would outlive a failed
    ingest and no longer match the store that is actually serving.
    """
    return Path(store_root) / FIGURE_DIR / doc_id


def figure_rel_path(doc_id: str, filename: str) -> str:
    """The store-relative path recorded in the database.

    Defined next to `figure_out_dir` because the two must agree: the writer
    builds a directory, the reader resolves a string, and a mismatch surfaces
    only as a broken image in the UI.
    """
    return f"{FIGURE_DIR}/{doc_id}/{filename}"


def _cluster(rects: list, gap: float = GAP) -> list:
    """Merge boxes that are within `gap` of each other, repeatedly.

    One pass is not enough: A near B and B near C must yield one box even when
    A and C are far apart, so this runs until nothing merges.
    """
    import pymupdf

    boxes = [pymupdf.Rect(r) for r in rects]
    merged = True
    while merged:
        merged = False
        out: list = []
        while boxes:
            current = boxes.pop()
            grown = pymupdf.Rect(current)
            grown.x0 -= gap
            grown.y0 -= gap
            grown.x1 += gap
            grown.y1 += gap
            for other in [b for b in boxes if grown.intersects(b)]:
                boxes.remove(other)
                current |= other
                merged = True
            out.append(current)
        boxes = out
    return boxes


def detect_figures(page) -> list[DetectedFigure]:
    """Illustrations on one page, in reading order (top to bottom)."""
    import pymupdf

    page_area = abs(page.rect)
    candidates: list = []

    for image in page.get_images(full=True):
        try:
            placements = page.get_image_rects(image[0])
        except Exception as exc:  # a malformed xref must not kill the page
            log.debug("p.%d: image rect lookup failed (%s)", page.number + 1, exc)
            continue
        for rect in placements:
            if rect.width >= MIN_PT and rect.height >= MIN_PT:
                candidates.append(pymupdf.Rect(rect))

    for drawing in page.get_drawings():
        rect = pymupdf.Rect(drawing["rect"])
        if rect.width < MIN_PT or rect.height < MIN_PT:
            continue
        if abs(rect) > page_area * PAGE_FRACTION:
            continue  # background panel
        candidates.append(rect)

    if not candidates:
        return []

    words = page.get_text("words")
    found: list[DetectedFigure] = []
    for box in _cluster(candidates):
        if box.width < MIN_PT or box.height < MIN_PT:
            continue
        if abs(box) > page_area * PAGE_FRACTION:
            continue
        inside = sum(1 for w in words if pymupdf.Rect(w[:4]) in box)
        if inside > MAX_WORDS_INSIDE:
            continue
        found.append(
            DetectedFigure(
                page=page.number + 1,
                bbox=(box.x0, box.y0, box.x1, box.y1),
                top=box.y0,
            )
        )

    found.sort(key=lambda f: f.top)
    return found


def render_figure(
    page, figure: DetectedFigure, out_dir: Path
) -> Optional[RenderedFigure]:
    """Render one figure into `out_dir`.

    The filename is the SHA-1 of the PNG bytes, so a diagram repeated across
    pages is written once — these manuals reuse the same handset illustration
    heavily. Returns None if the region renders to nothing.
    """
    import pymupdf

    try:
        pixmap = page.get_pixmap(clip=pymupdf.Rect(*figure.bbox), dpi=RENDER_DPI)
    except Exception as exc:
        log.warning("p.%d: figure render failed (%s)", figure.page, exc)
        return None
    if not pixmap.width or not pixmap.height:
        return None

    data = pixmap.tobytes("png")
    name = f"{hashlib.sha1(data).hexdigest()}.png"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    if not path.exists():  # content-addressed: identical bytes, identical name
        path.write_bytes(data)
    return RenderedFigure(
        page=figure.page, filename=name, width=pixmap.width, height=pixmap.height
    )
