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
