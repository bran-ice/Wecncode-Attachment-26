import pytest

from core.schema import Chunk, RetrievedChunk
from query.rerank import CrossEncoderReranker, NoopReranker, build_reranker


def hit(chunk_id, text, score=0.01, path="Getting started > Charging"):
    chunk = Chunk(doc_id="d", text=text, section_path=path, page_start=1, page_end=1,
                  chunk_id=chunk_id)
    return RetrievedChunk(chunk=chunk, score=score, source="rrf", rank=chunk_id)


class FakeCrossEncoder:
    """Scores by keyword overlap — enough to verify reordering and plumbing."""

    def __init__(self):
        self.pairs = None

    def predict(self, pairs):
        self.pairs = list(pairs)
        return [
            len(set(q.lower().split()) & set(p.lower().split())) for q, p in self.pairs
        ]


def test_reranker_reorders_by_relevance_not_retrieval_score():
    """The whole point: a bi-encoder scored these without seeing the question,
    so the fused order can be wrong at the top even when recall is fine."""
    model = FakeCrossEncoder()
    reranker = CrossEncoderReranker(model=model)
    hits = [
        hit(1, "The camera supports night mode for low light photography", score=0.9),
        hit(2, "Wireless power sharing charges another device from your battery", score=0.1),
    ]
    out = reranker.rerank("how do I charge another device wirelessly", hits, top_k=2)
    assert out[0].chunk.chunk_id == 2


def test_reranker_sees_the_section_path_not_just_the_body():
    """`embed_text()` prefixes the path — the same string the index was built
    from — so the reranker judges what was actually retrieved."""
    model = FakeCrossEncoder()
    CrossEncoderReranker(model=model).rerank("charging", [hit(1, "body text")], top_k=1)
    assert model.pairs[0][1].startswith("Getting started > Charging")


def test_reranker_truncates_to_top_k():
    reranker = CrossEncoderReranker(model=FakeCrossEncoder())
    hits = [hit(i, f"passage number {i} about charging") for i in range(1, 11)]
    assert len(reranker.rerank("charging", hits, top_k=3)) == 3


def test_reranker_relabels_source_and_rank():
    out = CrossEncoderReranker(model=FakeCrossEncoder()).rerank(
        "charging", [hit(1, "charging passage"), hit(2, "other")], top_k=2
    )
    assert [h.source for h in out] == ["rerank", "rerank"]
    assert [h.rank for h in out] == [0, 1]


def test_reranker_on_empty_input_does_not_call_the_model():
    model = FakeCrossEncoder()
    assert CrossEncoderReranker(model=model).rerank("q", [], top_k=5) == []
    assert model.pairs is None


def test_noop_reranker_preserves_fusion_order():
    """The ablation arm that isolates retrieval from reranking."""
    hits = [hit(1, "alpha"), hit(2, "beta"), hit(3, "gamma")]
    out = NoopReranker().rerank("anything", hits, top_k=2)
    assert [h.chunk.chunk_id for h in out] == [1, 2]


def test_build_reranker_selects_the_arm():
    assert isinstance(build_reranker(enabled=False), NoopReranker)
    assert isinstance(build_reranker(enabled=True, model=FakeCrossEncoder()),
                      CrossEncoderReranker)


@pytest.mark.live
def test_live_reranker_prefers_the_relevant_passage():
    """Guards the real model, not a stub: the cross-encoder must rank an
    on-topic passage above an off-topic one that retrieval scored higher."""
    reranker = CrossEncoderReranker()
    hits = [
        hit(1, "Open the Camera app and tap the shutter button to take a photo.", score=0.9),
        hit(2, "To take a screenshot, press the Side button and Volume Down "
                "button at the same time.", score=0.1),
    ]
    out = reranker.rerank("what buttons do I press for a screenshot", hits, top_k=2)
    assert out[0].chunk.chunk_id == 2


def test_reranking_is_off_by_default():
    """Measured: +0.02 R@1, -0.02 R@5, flat MRR, 280x latency. Opting in must be
    a deliberate act, not the default."""
    from core.config import load_settings
    from query.rerank import build_reranker_from_settings

    import os
    os.environ.pop("RERANK", None)
    assert isinstance(build_reranker_from_settings(load_settings(require_api_key=False)),
                      NoopReranker)


def test_rerank_env_var_enables_it(monkeypatch):
    from core.config import load_settings
    from query.rerank import build_reranker_from_settings

    monkeypatch.setenv("RERANK", "true")
    reranker = build_reranker_from_settings(load_settings(require_api_key=False),
                                            model=FakeCrossEncoder())
    assert isinstance(reranker, CrossEncoderReranker)
