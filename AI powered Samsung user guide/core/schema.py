"""Data types shared by the ingestion and query pipelines.

These are the only structures that cross the pipeline boundary, so changes here
are changes to the contract between them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Document:
    """One source manual."""

    doc_id: str  # stable: sha256 of the file
    model: str  # e.g. "Galaxy S24 Ultra"
    title: str
    url: str
    sha256: str
    n_pages: int
    language: str = "en"
    region: Optional[str] = None
    os_version: Optional[str] = None
    ingested_at: Optional[str] = None  # ISO8601, set by the store on write


@dataclass
class Figure:
    """One illustration lifted from a manual page.

    `rel_path` is relative to the store root, never absolute: the store
    directory is renamed during the atomic swap and may be moved wholesale, and
    an absolute path baked in at ingest would survive neither.

    A figure is a *rendered region*, not an extracted image. Samsung draws the
    callout lines and labels as vector paths on top of a raster screenshot, so
    the embedded image on its own is the photo with none of the annotation that
    makes it instructional. See `ingest/figures.py`.
    """

    doc_id: str
    page: int  # 1-based, matching the citation
    rel_path: str
    width: int
    height: int
    figure_id: Optional[int] = None  # assigned by the store


@dataclass
class Chunk:
    """A retrievable span of one document.

    `section_path` is prefixed onto `text` at embed time; it is what makes a
    citation readable and what rescues retrieval on very short questions.
    """

    doc_id: str
    text: str
    page_start: int
    page_end: int
    section_path: str = ""
    token_count: int = 0
    chunk_id: Optional[int] = None  # assigned by the store
    vector_id: Optional[int] = None  # FAISS row; equals chunk_id once indexed
    # Figures whose place in reading order falls inside this chunk's span.
    # Populated at chunk time and persisted through `chunk_figures`; never
    # part of `embed_text()` — a figure must not perturb ranking.
    figures: list[Figure] = field(default_factory=list)

    def embed_text(self) -> str:
        """The string actually sent to the embedding model."""
        return f"{self.section_path}\n\n{self.text}".strip() if self.section_path else self.text


@dataclass
class RetrievedChunk:
    """A chunk plus why it came back."""

    chunk: Chunk
    score: float
    source: str  # "bm25" | "dense" | "rrf" | "rerank"
    rank: Optional[int] = None


@dataclass
class Citation:
    """A `[n]` marker in a generated answer, resolved back to its source."""

    marker: int
    chunk_id: int
    model: str
    page_start: int
    page_end: int
    section_path: str
    snippet: str
    # Figures on the cited chunk. Citation is what makes a figure renderable:
    # an answer that never used a passage should not illustrate itself with it.
    figures: list[Figure] = field(default_factory=list)

    def label(self) -> str:
        pages = (
            f"p.{self.page_start}"
            if self.page_start == self.page_end
            else f"pp.{self.page_start}-{self.page_end}"
        )
        return f"{self.model} {pages}"


@dataclass
class Answer:
    """The result of one query-pipeline run."""

    question: str
    text: str
    citations: list[Citation] = field(default_factory=list)
    retrieved: list[RetrievedChunk] = field(default_factory=list)
    refused: bool = False
    latency_ms: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None

    def figures(self) -> list[tuple[Figure, int]]:
        """Figures to show with this answer, as `(figure, marker)`.

        Ordered by first citation, deduplicated on `rel_path`: two cited chunks
        in one section frequently carry the same diagram, and rendering it
        twice reads as a UI bug. A refusal shows nothing — there is no claim
        for a picture to illustrate.
        """
        if self.refused:
            return []
        out: list[tuple[Figure, int]] = []
        seen: set[str] = set()
        for citation in self.citations:
            for figure in citation.figures:
                if figure.rel_path in seen:
                    continue
                seen.add(figure.rel_path)
                out.append((figure, citation.marker))
        return out
