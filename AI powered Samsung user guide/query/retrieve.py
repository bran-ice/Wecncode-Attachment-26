"""Hybrid retrieval: keyword search and vector search, fused.

Neither half is sufficient on its own for a product manual:

* **BM25** matches literal strings. It is the only thing that reliably finds
  `EP-TA845`, `SM-S928W`, or a menu path typed verbatim. It fails completely
  when the user's words differ from the manual's ("slow charging" vs "reduced
  charging speed").
* **Dense vectors** match meaning, and handle that rephrasing. They are actively
  bad at part numbers — `EP-TA845` and `EP-TA800` are near-identical in
  embedding space, which is precisely the wrong answer.

The two ranked lists are combined with Reciprocal Rank Fusion, which needs no
score normalisation — a real advantage when one score is a BM25 magnitude and
the other a cosine similarity, quantities with no common scale.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from core.logging_setup import get_logger
from core.schema import RetrievedChunk
from core.storage import Store

log = get_logger(__name__)

RRF_K = 60  # standard damping constant; larger => flatter weighting of top ranks
CANDIDATES = 30  # per retriever, before fusion

# Fusion weights. Equal weighting is the textbook default, but the two arms are
# not equally reliable *per query type*: measured over 54 questions, BM25 leads
# on verbatim strings (MRR 0.90 vs 0.64) while dense leads on natural language
# (0.84 vs 0.67). A fixed compromise loses one or the other — downweighting BM25
# to 0.7 lifted natural MRR 0.777 -> 0.831 but dropped verbatim 0.900 -> 0.740.
# So the weight is chosen per query instead. See eval/RESULTS.md.
BM25_WEIGHT = 1.0  # exact-string queries: BM25 is authoritative
BM25_WEIGHT_PROSE = 0.7  # natural language: let dense lead
DENSE_WEIGHT = 1.0

# A token that mixes letters and digits ("IP68", "45W", "SM-A155F", "HDR10") or
# is all-caps ("HEIF", "NFC") is the kind of literal string dense retrieval
# blurs together. Short queries are treated the same way: someone typing two
# words is naming a thing, not describing a problem.
_LITERAL_TOKEN = re.compile(r"[A-Za-z]+-?\d|\d+[A-Za-z]|[A-Z]{2,}")


def adaptive_bm25_weight(query: str) -> float:
    """Trust BM25 fully when the query looks like an exact string."""
    tokens = query.split()
    if len(tokens) <= 3 or any(_LITERAL_TOKEN.search(t) for t in tokens):
        return BM25_WEIGHT
    return BM25_WEIGHT_PROSE


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk]
    bm25_count: int = 0
    dense_count: int = 0
    collapsed_duplicates: int = 0


def rrf_fuse(
    ranked_lists: Sequence[Sequence[RetrievedChunk]],
    k: int = RRF_K,
    weights: Optional[Sequence[float]] = None,
) -> list[RetrievedChunk]:
    """Reciprocal Rank Fusion: score = Σ wᵢ/(k + rank).

    Rank-based, not score-based, so BM25 magnitudes and cosine similarities can
    be combined without normalising either. A chunk found by *both* retrievers
    accumulates from both lists, which is exactly the signal we want.

    `weights` exists because the two retrievers are not equally strong on this
    corpus: measured over 54 questions, dense leads on natural-language queries
    (MRR 0.84 vs 0.67) while BM25 leads on verbatim strings (0.90 vs 0.64).
    Equal weighting lets the weaker arm displace the stronger one's top hits.
    """
    scores: dict[int, float] = {}
    best: dict[int, RetrievedChunk] = {}
    weights = list(weights) if weights else [1.0] * len(ranked_lists)

    for weight, ranked in zip(weights, ranked_lists):
        for rank, hit in enumerate(ranked):
            chunk_id = hit.chunk.chunk_id
            scores[chunk_id] = scores.get(chunk_id, 0.0) + weight / (k + rank + 1)
            # Keep whichever copy we saw first; identity is the chunk, not the
            # retriever that surfaced it.
            best.setdefault(chunk_id, hit)

    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [
        RetrievedChunk(
            chunk=best[chunk_id].chunk, score=score, source="rrf", rank=position
        )
        for position, (chunk_id, score) in enumerate(ordered)
    ]


NEAR_DUPLICATE_JACCARD = 0.85


def _token_set(text: str) -> frozenset[str]:
    return frozenset(re.findall(r"[a-z0-9]+", text.lower()))


def dedupe_by_text(
    hits: Iterable[RetrievedChunk], threshold: float = NEAR_DUPLICATE_JACCARD
) -> tuple[list[RetrievedChunk], int]:
    """Collapse duplicate and near-duplicate passages, keeping the best-ranked.

    43% of this corpus is byte-identical boilerplate — the "Settings > Google"
    passage exists in 22 manuals. Worse, successive manual revisions reword a
    sentence or two, so many copies are *near* duplicates that an exact match
    misses entirely: a real query returned three copies of the same charging
    warning differing only by the word "An".

    Left alone, one question fills the whole top-k with one passage and crowds
    out everything else. Reranking cannot fix it — every copy is equally
    relevant, which is precisely the problem. Jaccard over token sets is cheap
    at this scale (tens of candidates) and robust to that kind of rewording.
    """
    kept: list[RetrievedChunk] = []
    signatures: list[frozenset[str]] = []
    collapsed = 0

    for hit in hits:
        tokens = _token_set(hit.chunk.text)
        if not tokens:
            continue
        duplicate = False
        for existing in signatures:
            overlap = len(tokens & existing)
            if not overlap:
                continue
            union = len(tokens | existing)
            if union and overlap / union >= threshold:
                duplicate = True
                break
        if duplicate:
            collapsed += 1
            continue
        kept.append(hit)
        signatures.append(tokens)

    return kept, collapsed


def filter_by_model(
    hits: Iterable[RetrievedChunk], store: Store, model_query: str
) -> list[RetrievedChunk]:
    """Keep only chunks from manuals covering the model the user named.

    Matching is on model *codes* as well as display names because one manual
    serves a whole family — asking about an S24 Ultra must match the manual whose
    label reads "Galaxy S24/S25 series".
    """
    wanted = model_query.lower().replace("galaxy", "").strip()
    if not wanted:
        return list(hits)

    allowed: set[str] = set()
    for document in store.list_documents():
        haystack = f"{document.model} {document.title}".lower()
        if wanted in haystack or any(
            token and token in haystack for token in wanted.split()
        ):
            allowed.add(document.doc_id)

    if not allowed:
        return list(hits)  # unknown model: better to answer broadly than not at all
    return [hit for hit in hits if hit.chunk.doc_id in allowed]


def retrieve(
    store: Store,
    query: str,
    embedder=None,
    queries: Optional[Sequence[str]] = None,
    mode: str = "hybrid",
    candidates: int = CANDIDATES,
    top_k: int = 20,
    model_filter: Optional[str] = None,
    bm25_weight: Optional[float] = None,
    dense_weight: float = DENSE_WEIGHT,
) -> RetrievalResult:
    """Run the configured retrievers and fuse their results.

    `mode` is "hybrid", "bm25" or "dense" — the three arms of the Phase 7
    ablation, which is why they share one entry point.
    """
    search_queries = list(queries) if queries else [query]
    if bm25_weight is None:
        bm25_weight = adaptive_bm25_weight(query)

    bm25_hits: list[RetrievedChunk] = []
    dense_hits: list[RetrievedChunk] = []
    lists: list[list[RetrievedChunk]] = []
    weights: list[float] = []

    if mode in ("hybrid", "bm25"):
        for search_query in search_queries:
            hits = store.search_bm25(search_query, k=candidates)
            bm25_hits.extend(hits)
            lists.append(hits)
            weights.append(bm25_weight)

    if mode in ("hybrid", "dense"):
        if embedder is None:
            raise ValueError("dense retrieval needs an embedder")
        for search_query in search_queries:
            vector = embedder.embed_query(search_query)
            hits = store.search_dense(vector, k=candidates)
            dense_hits.extend(hits)
            lists.append(hits)
            weights.append(dense_weight)

    fused = rrf_fuse(lists, weights=weights)
    if model_filter:
        fused = filter_by_model(fused, store, model_filter)
    deduped, collapsed = dedupe_by_text(fused)

    return RetrievalResult(
        chunks=deduped[:top_k],
        bm25_count=len(bm25_hits),
        dense_count=len(dense_hits),
        collapsed_duplicates=collapsed,
    )
