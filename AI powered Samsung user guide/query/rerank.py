"""Rerank fused candidates with a cross-encoder.

Retrieval is a *bi-encoder* process: query and passage are embedded separately
and compared by cosine distance. That is fast — it lets us search 4,630 vectors
in milliseconds — but the passage vector is computed with no knowledge of the
question, so the comparison is necessarily coarse.

A **cross-encoder** reads the query and the passage *together* in one forward
pass and outputs a single relevance score. It cannot be pre-computed and it
cannot scale to a whole corpus, but over ~20 candidates it is cheap and
substantially sharper. This is the standard retrieve-then-rerank arrangement.
"""

from __future__ import annotations

from typing import Optional, Sequence

from core.logging_setup import get_logger
from core.schema import RetrievedChunk

log = get_logger(__name__)

RERANK_MODEL = "BAAI/bge-reranker-base"


class CrossEncoderReranker:
    """Local cross-encoder. Loaded lazily — it is not needed for BM25-only runs."""

    def __init__(self, model_name: str = RERANK_MODEL, model=None):
        self.model_name = model_name
        self._model = model

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            log.info("Loading reranker %s (first run downloads ~1.1GB)", self.model_name)
            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(
        self, query: str, hits: Sequence[RetrievedChunk], top_k: int = 5
    ) -> list[RetrievedChunk]:
        if not hits:
            return []
        pairs = [(query, hit.chunk.embed_text()) for hit in hits]
        scores = self.model.predict(pairs)

        ordered = sorted(zip(hits, scores), key=lambda pair: pair[1], reverse=True)
        return [
            RetrievedChunk(
                chunk=hit.chunk, score=float(score), source="rerank", rank=position
            )
            for position, (hit, score) in enumerate(ordered[:top_k])
        ]


class NoopReranker:
    """Passthrough, for the ablation arm that measures retrieval without rerank."""

    def rerank(
        self, query: str, hits: Sequence[RetrievedChunk], top_k: int = 5
    ) -> list[RetrievedChunk]:
        return list(hits[:top_k])


def build_reranker(
    enabled: bool = False, model: Optional[object] = None,
    model_name: str = RERANK_MODEL,
):
    """Off by default — see `Settings.rerank_enabled` for the measurements."""
    return (
        CrossEncoderReranker(model_name=model_name, model=model)
        if enabled
        else NoopReranker()
    )


def build_reranker_from_settings(settings, model: Optional[object] = None):
    return build_reranker(
        enabled=settings.rerank_enabled, model=model,
        model_name=settings.rerank_model,
    )
