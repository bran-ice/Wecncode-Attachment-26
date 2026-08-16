import pytest

from core.schema import Chunk, RetrievedChunk
from query.retrieve import (
    dedupe_by_text,
    filter_by_model,
    rrf_fuse,
    retrieve,
)


def hit(chunk_id, text="some passage about charging the battery", rank=0, doc="d1",
        path="Getting started > Charging"):
    chunk = Chunk(doc_id=doc, text=text, section_path=path, page_start=1, page_end=1,
                  chunk_id=chunk_id)
    return RetrievedChunk(chunk=chunk, score=1.0, source="bm25", rank=rank)


# ----------------------------------------------------------------------- RRF


def test_rrf_scores_match_the_formula():
    """score = 1/(k + rank), ranks 1-based."""
    fused = rrf_fuse([[hit(1), hit(2)]], k=60)
    assert fused[0].score == pytest.approx(1 / 61)
    assert fused[1].score == pytest.approx(1 / 62)


def test_chunk_found_by_both_retrievers_outranks_either_alone():
    """The core value of fusion: agreement between two different signals."""
    bm25 = [hit(1), hit(2, "unrelated text about the camera app")]
    dense = [hit(3, "different passage about wireless power sharing"), hit(1)]
    fused = rrf_fuse([bm25, dense])
    assert fused[0].chunk.chunk_id == 1
    assert fused[0].score == pytest.approx(1 / 61 + 1 / 62)


def test_rrf_needs_no_score_normalisation():
    """BM25 magnitudes and cosine similarities share no scale; RRF uses only
    rank, so wildly different score ranges must not change the outcome."""
    a = [hit(1), hit(2)]
    b = [hit(2), hit(1)]
    for h, value in zip(a + b, [900.0, 12.5, 0.81, 0.79]):
        h.score = value
    fused = rrf_fuse([a, b])
    assert {f.chunk.chunk_id for f in fused} == {1, 2}
    assert fused[0].score == pytest.approx(1 / 61 + 1 / 62)


def test_empty_lists_fuse_to_nothing():
    assert rrf_fuse([[], []]) == []


# ------------------------------------------------------------------- dedupe


def test_identical_passages_collapse():
    """43% of the corpus is byte-identical boilerplate across manuals."""
    text = "Configure settings for some features provided by Google."
    kept, collapsed = dedupe_by_text([hit(i, text, doc=f"d{i}") for i in range(1, 6)])
    assert len(kept) == 1 and collapsed == 4
    assert kept[0].chunk.chunk_id == 1  # the best-ranked copy survives


def test_near_duplicates_collapse_too():
    """Manual revisions reword a sentence or two. Exact matching missed these:
    a real query returned three copies of one charging warning differing by the
    word "An"."""
    base = ("Use only Samsung-approved battery, charger, and cable specifically "
            "designed for your device. Incompatible battery, charger, or cable "
            "can cause serious injuries or damage to your device.")
    variant = base.replace("Incompatible", "An incompatible")
    kept, collapsed = dedupe_by_text([hit(1, base), hit(2, variant)])
    assert len(kept) == 1 and collapsed == 1


def test_genuinely_different_passages_are_kept():
    kept, collapsed = dedupe_by_text([
        hit(1, "Wireless power sharing lets you charge another device."),
        hit(2, "Take a screenshot by pressing the Side and Volume Down buttons."),
        hit(3, "Add a second language to the keyboard in Settings."),
    ])
    assert len(kept) == 3 and collapsed == 0


def test_dedupe_preserves_ranking_order():
    kept, _ = dedupe_by_text([hit(1, "alpha text here"), hit(2, "beta text here"),
                              hit(3, "alpha text here")])
    assert [k.chunk.chunk_id for k in kept] == [1, 2]


def test_dedupe_threshold_is_tunable():
    a = hit(1, "one two three four five six seven eight")
    b = hit(2, "one two three four five six seven nine")
    assert len(dedupe_by_text([a, b], threshold=0.99)[0]) == 2
    assert len(dedupe_by_text([a, b], threshold=0.5)[0]) == 1


# ------------------------------------------------------------- model filter


class FakeDoc:
    def __init__(self, doc_id, model, title=""):
        self.doc_id = doc_id
        self.model = model
        self.title = title


class FakeStore:
    def __init__(self, docs):
        self._docs = docs

    def list_documents(self):
        return self._docs


def test_model_filter_matches_a_family_manual():
    """One manual serves seven phones: asking about an S24 Ultra must match the
    manual labelled "Galaxy S24/S25 series"."""
    store = FakeStore([FakeDoc("d1", "Galaxy S24/S25 series"),
                       FakeDoc("d2", "Galaxy Z Fold6")])
    hits = [hit(1, doc="d1"), hit(2, doc="d2")]
    kept = filter_by_model(hits, store, "S24 Ultra")
    assert [k.chunk.doc_id for k in kept] == ["d1"]


def test_unknown_model_does_not_empty_the_results():
    """Answering broadly beats answering nothing when the model is unrecognised."""
    store = FakeStore([FakeDoc("d1", "Galaxy S24/S25 series")])
    hits = [hit(1, doc="d1")]
    assert len(filter_by_model(hits, store, "Nokia 3310")) == 1


# ----------------------------------------------------------------- retrieve


class StubStore(FakeStore):
    def __init__(self, bm25=None, dense=None, docs=()):
        super().__init__(list(docs))
        self._bm25 = bm25 or []
        self._dense = dense or []
        self.bm25_queries: list[str] = []
        self.dense_calls = 0

    def search_bm25(self, query, k=30):
        self.bm25_queries.append(query)
        return self._bm25[:k]

    def search_dense(self, vector, k=30):
        self.dense_calls += 1
        return self._dense[:k]


class StubEmbedder:
    dim = 8

    def embed_query(self, text):
        return [0.0] * 8


def test_bm25_mode_never_touches_the_embedder():
    store = StubStore(bm25=[hit(1)])
    result = retrieve(store, "EP-TA845", embedder=None, mode="bm25")
    assert result.dense_count == 0 and result.bm25_count == 1


def test_dense_mode_requires_an_embedder():
    with pytest.raises(ValueError, match="embedder"):
        retrieve(StubStore(), "question", embedder=None, mode="dense")


def test_hybrid_runs_both_retrievers():
    store = StubStore(bm25=[hit(1)], dense=[hit(2, "a different passage entirely")])
    result = retrieve(store, "q", embedder=StubEmbedder(), mode="hybrid")
    assert result.bm25_count == 1 and result.dense_count == 1
    assert {c.chunk.chunk_id for c in result.chunks} == {1, 2}


def test_expanded_queries_all_get_searched():
    store = StubStore(bm25=[hit(1)])
    retrieve(store, "original", queries=["one", "two", "three"], mode="bm25")
    assert store.bm25_queries == ["one", "two", "three"]


def test_top_k_is_applied_after_dedupe():
    """Trimming before dedupe would let duplicates consume the budget."""
    duplicates = [hit(i, "identical boilerplate passage", doc=f"d{i}") for i in range(1, 6)]
    unique = [hit(9, "a genuinely different passage about the camera")]
    store = StubStore(bm25=duplicates + unique)
    result = retrieve(store, "q", mode="bm25", top_k=2)
    assert len(result.chunks) == 2
    assert {c.chunk.chunk_id for c in result.chunks} == {1, 9}


# ------------------------------------------------------- adaptive weighting


@pytest.mark.parametrize("query", ["IP68", "45W charger", "SM-A155F", "HEIF format",
                                   "USB Type-C cable", "Smart Switch"])
def test_literal_queries_keep_bm25_at_full_weight(query):
    """Exact strings are the one case BM25 is authoritative: dense retrieval
    puts IP68 and IP67 in nearly the same place."""
    from query.retrieve import BM25_WEIGHT, adaptive_bm25_weight

    assert adaptive_bm25_weight(query) == BM25_WEIGHT


@pytest.mark.parametrize("query", [
    "how do I keep the clock showing when the screen is off",
    "why does my phone get hot while charging",
    "what can I do to make the battery last longer",
])
def test_prose_queries_let_dense_lead(query):
    from query.retrieve import BM25_WEIGHT_PROSE, adaptive_bm25_weight

    assert adaptive_bm25_weight(query) == BM25_WEIGHT_PROSE


def test_weighted_fusion_changes_ranking():
    """A weight of 0 must remove that arm's influence entirely."""
    bm25 = [hit(1, "keyword winner passage")]
    dense = [hit(2, "semantic winner passage")]
    assert rrf_fuse([bm25, dense], weights=[0.0, 1.0])[0].chunk.chunk_id == 2
    assert rrf_fuse([bm25, dense], weights=[1.0, 0.0])[0].chunk.chunk_id == 1


def test_weights_default_to_equal():
    fused = rrf_fuse([[hit(1)], [hit(2, "other passage")]])
    assert fused[0].score == pytest.approx(fused[1].score)
