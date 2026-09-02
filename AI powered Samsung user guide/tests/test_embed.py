"""Embedding tests. Gemini is mocked throughout; the one live test is marked."""

import numpy as np
import pytest

from ingest.embed import (
    DOCUMENT_TASK,
    QUERY_TASK,
    EmbeddingCache,
    EmbeddingError,
    GeminiEmbedder,
    RateLimiter,
    cache_key,
)


def unlimited() -> RateLimiter:
    """A limiter that never blocks — rate limiting is tested on its own below,
    and the real one would otherwise wait against a real clock in every test."""
    return RateLimiter(per_minute=10**9, sleep=lambda s: None)


class FakeEmbedding:
    def __init__(self, values):
        self.values = values


class FakeResponse:
    def __init__(self, embeddings):
        self.embeddings = embeddings


class FakeModels:
    """Records every call, and can be told to fail the first N times."""

    def __init__(self, dim=8, fail_times=0, error="429 RESOURCE_EXHAUSTED", short_by=0):
        self.dim = dim
        self.fail_times = fail_times
        self.error = error
        self.short_by = short_by
        self.calls: list[dict] = []

    def embed_content(self, model, contents, config):
        self.calls.append(
            {"model": model, "contents": list(contents), "task": config.task_type}
        )
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError(self.error)
        out = []
        for i, text in enumerate(contents):
            # Deterministic per-text vector so identity is checkable.
            seed = abs(hash(text)) % 1000
            out.append(FakeEmbedding([float(seed + i)] * self.dim))
        if self.short_by:
            out = out[: len(out) - self.short_by]
        return FakeResponse(out)


class FakeClient:
    def __init__(self, models):
        self.models = models


@pytest.fixture
def models():
    return FakeModels()


@pytest.fixture
def embedder(models, tmp_path):
    return GeminiEmbedder(
        api_key="k",
        dim=8,
        cache=EmbeddingCache(tmp_path / "cache.db"),
        client=FakeClient(models),
        sleep=lambda s: None,
        limiter=unlimited(),
    )


# --------------------------------------------------------------------- basics


def test_returns_one_vector_per_text_in_order(embedder):
    out = embedder.embed_texts(["alpha", "beta", "gamma"])
    assert out.shape == (3, 8)
    again = embedder.embed_texts(["gamma", "alpha"])
    assert np.array_equal(again[0], out[2])
    assert np.array_equal(again[1], out[0])


def test_documents_and_queries_use_different_task_types(embedder, models):
    embedder.embed_texts(["a passage about charging"])
    embedder.embed_query("how do I charge it")
    assert models.calls[0]["task"] == DOCUMENT_TASK
    assert models.calls[1]["task"] == QUERY_TASK


def test_batches_respect_the_batch_size(embedder, models):
    embedder.embed_texts([f"text {i}" for i in range(120)], batch_size=50)
    assert [len(c["contents"]) for c in models.calls] == [50, 50, 20]


def test_empty_input_makes_no_calls(embedder, models):
    assert embedder.embed_texts([]).shape == (0, 8)
    assert models.calls == []


# ---------------------------------------------------------------- not paying twice


def test_second_run_makes_no_api_calls(embedder, models):
    texts = ["alpha", "beta"]
    embedder.embed_texts(texts)
    calls_after_first = len(models.calls)
    embedder.embed_texts(texts)
    assert len(models.calls) == calls_after_first


def test_only_changed_texts_are_re_embedded(embedder, models):
    embedder.embed_texts(["alpha", "beta"])
    models.calls.clear()
    embedder.embed_texts(["alpha", "beta", "gamma"])
    assert [c["contents"] for c in models.calls] == [["gamma"]]


def test_duplicate_texts_are_embedded_once(embedder, models):
    """Manuals repeat boilerplate verbatim across models — the same safety
    paragraph can appear a dozen times in one corpus."""
    out = embedder.embed_texts(["same"] * 5 + ["other"])
    assert sorted(models.calls[0]["contents"]) == ["other", "same"]
    assert out.shape == (6, 8)
    assert np.array_equal(out[0], out[4])


def test_cache_survives_a_new_embedder(tmp_path, models):
    cache_path = tmp_path / "c.db"
    first = GeminiEmbedder("k", dim=8, cache=EmbeddingCache(cache_path),
                           client=FakeClient(models), sleep=lambda s: None,
                           limiter=unlimited())
    first.embed_texts(["alpha"])
    models.calls.clear()

    second = GeminiEmbedder("k", dim=8, cache=EmbeddingCache(cache_path),
                            client=FakeClient(models), sleep=lambda s: None,
                            limiter=unlimited())
    second.embed_texts(["alpha"])
    assert models.calls == []  # a crashed run resumes instead of re-paying


def test_cache_key_separates_task_types_and_dimensions():
    """A query vector must never be served from a document embedding."""
    base = ("text", "gemini-embedding-001", DOCUMENT_TASK, 768)
    assert cache_key(*base) != cache_key("text", "gemini-embedding-001", QUERY_TASK, 768)
    assert cache_key(*base) != cache_key("text", "gemini-embedding-001", DOCUMENT_TASK, 1536)
    assert cache_key(*base) != cache_key("other", "gemini-embedding-001", DOCUMENT_TASK, 768)
    assert cache_key(*base) == cache_key(*base)


# ------------------------------------------------------------------- failures


def test_rate_limit_is_retried_then_succeeds(tmp_path):
    models = FakeModels(dim=8, fail_times=2)
    slept = []
    embedder = GeminiEmbedder("k", dim=8, cache=EmbeddingCache(tmp_path / "c.db"),
                              client=FakeClient(models), sleep=slept.append,
                              limiter=unlimited())
    assert embedder.embed_texts(["alpha"]).shape == (1, 8)
    assert slept == [5.0, 10.0]  # exponential backoff


def test_non_retryable_error_fails_fast(tmp_path):
    models = FakeModels(dim=8, fail_times=99, error="400 INVALID_ARGUMENT")
    embedder = GeminiEmbedder("k", dim=8, cache=EmbeddingCache(tmp_path / "c.db"),
                              client=FakeClient(models), sleep=lambda s: None,
                              limiter=unlimited())
    with pytest.raises(EmbeddingError, match="INVALID_ARGUMENT"):
        embedder.embed_texts(["alpha"])
    assert len(models.calls) == 1  # no pointless retries


def test_dropped_tls_handshake_is_retried(tmp_path):
    """A transport failure carries no HTTP status, so a status-token-only retry
    check treats it as fatal and kills the chat turn on one flaky connection."""
    error = "[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol"
    models = FakeModels(dim=8, fail_times=2, error=error)
    embedder = GeminiEmbedder("k", dim=8, cache=EmbeddingCache(tmp_path / "c.db"),
                              client=FakeClient(models), sleep=lambda s: None,
                              limiter=unlimited())
    assert embedder.embed_texts(["alpha"]).shape == (1, 8)
    assert len(models.calls) == 3


def test_gives_up_after_max_retries(tmp_path):
    models = FakeModels(dim=8, fail_times=99)
    embedder = GeminiEmbedder("k", dim=8, cache=EmbeddingCache(tmp_path / "c.db"),
                              client=FakeClient(models), sleep=lambda s: None,
                              limiter=unlimited())
    with pytest.raises(EmbeddingError):
        embedder.embed_texts(["alpha"])
    assert len(models.calls) == 8


def test_short_response_is_rejected_rather_than_misaligned(tmp_path):
    """If vectors and chunks misalign, every citation silently points at the
    wrong passage — far worse than a failed build."""
    models = FakeModels(dim=8, short_by=1)
    embedder = GeminiEmbedder("k", dim=8, cache=EmbeddingCache(tmp_path / "c.db"),
                              client=FakeClient(models), sleep=lambda s: None,
                              limiter=unlimited())
    with pytest.raises(EmbeddingError, match="misalign"):
        embedder.embed_texts(["alpha", "beta"])


def test_partial_progress_is_kept_when_a_later_batch_fails(tmp_path):
    """Checkpointing per batch: a failure at batch 3 must not discard 1 and 2."""
    class FlakyModels(FakeModels):
        def embed_content(self, model, contents, config):
            if len(self.calls) >= 2:
                raise RuntimeError("400 INVALID_ARGUMENT")
            return super().embed_content(model, contents, config)

    models = FlakyModels(dim=8)
    cache = EmbeddingCache(tmp_path / "c.db")
    embedder = GeminiEmbedder("k", dim=8, cache=cache, client=FakeClient(models),
                              sleep=lambda s: None, limiter=unlimited())
    with pytest.raises(EmbeddingError):
        embedder.embed_texts([f"t{i}" for i in range(30)], batch_size=10)
    assert cache.count() == 20


# ----------------------------------------------------------------------- cache


def test_cache_roundtrip_preserves_values(tmp_path):
    cache = EmbeddingCache(tmp_path / "c.db")
    vec = np.array([0.5, -0.25, 0.125], dtype="float32")
    cache.put_many([("k1", vec)])
    assert np.array_equal(cache.get_many(["k1"])["k1"], vec)
    assert cache.get_many(["missing"]) == {}


def test_cache_handles_more_keys_than_sqlite_parameter_limit(tmp_path):
    cache = EmbeddingCache(tmp_path / "c.db")
    vectors = [(f"k{i}", np.zeros(4, dtype="float32")) for i in range(1200)]
    cache.put_many(vectors)
    assert len(cache.get_many([k for k, _ in vectors])) == 1200


@pytest.mark.live
def test_live_gemini_embedding_shape_and_task_types():
    """Guards the two assumptions the whole index rests on: 768 dimensions, and
    that query and document embeddings differ."""
    from core.config import load_settings

    settings = load_settings()
    embedder = GeminiEmbedder(settings.gemini_api_key, model=settings.embed_model)
    doc = embedder.embed_texts(["Wireless power sharing charges another device."])
    query = embedder.embed_query("how do I share my battery")
    assert doc.shape == (1, 768)
    assert query.shape == (768,)
    assert not np.allclose(doc[0], query)


# ------------------------------------------------------------------ rate limit


def test_rate_limiter_paces_below_the_quota():
    """Free tier counts *items*, not requests: a batch of 50 spends 50."""
    from ingest.embed import RateLimiter

    now = [0.0]
    slept = []

    def sleep(s):
        slept.append(s)
        now[0] += s

    limiter = RateLimiter(per_minute=90, sleep=sleep, clock=lambda: now[0])
    limiter.acquire(50)
    limiter.acquire(30)
    assert slept == []          # 80 of 90 spent, still under
    limiter.acquire(50)         # would be 130 — must wait for the window
    assert slept and slept[0] > 59


def test_rate_limiter_forgets_old_usage():
    from ingest.embed import RateLimiter

    now = [0.0]
    limiter = RateLimiter(per_minute=90, sleep=lambda s: None, clock=lambda: now[0])
    limiter.acquire(90)
    now[0] = 61.0
    limiter.acquire(90)
    assert limiter._spent() == 90  # the first window has rolled off


def test_server_retry_hint_is_honoured(tmp_path):
    """Gemini says how long to wait; that beats our guess."""
    models = FakeModels(dim=8, fail_times=1,
                        error="429 RESOURCE_EXHAUSTED retryDelay: '47s'")
    slept = []
    embedder = GeminiEmbedder("k", dim=8, cache=EmbeddingCache(tmp_path / "c.db"),
                              client=FakeClient(models), sleep=slept.append,
                              limiter=unlimited())
    embedder.embed_texts(["alpha"])
    assert slept[0] == pytest.approx(49.0)


def test_batch_size_must_divide_the_quota_window():
    """A batch that doesn't divide the per-minute quota halves throughput: with
    90/min and batches of 50, the second batch always waits a full window, so
    only 50 items move per minute instead of 90."""
    from ingest.embed import BATCH_SIZE, ITEMS_PER_MINUTE

    assert ITEMS_PER_MINUTE % BATCH_SIZE == 0


# ------------------------------------------------------------- local backend


class FakeSentenceModel:
    """Stands in for SentenceTransformer: records what it was asked to encode."""

    def __init__(self, dim=384):
        self.dim = dim
        self.encoded: list[list[str]] = []

    def get_sentence_embedding_dimension(self):
        return self.dim

    def encode(self, texts, **kwargs):
        self.encoded.append(list(texts))
        return np.array([[float(abs(hash(t)) % 100)] * self.dim for t in texts],
                        dtype="float32")


def local(tmp_path, model=None):
    from ingest.embed import LocalEmbedder

    return LocalEmbedder(cache=EmbeddingCache(tmp_path / "l.db"),
                         model=model or FakeSentenceModel())


def test_local_embedder_returns_vectors_in_order(tmp_path):
    embedder = local(tmp_path)
    out = embedder.embed_texts(["alpha", "beta", "gamma"])
    assert out.shape == (3, 384)
    assert np.array_equal(embedder.embed_texts(["beta"])[0], out[1])


def test_local_queries_get_the_bge_instruction_prefix(tmp_path):
    """BGE is trained with a query-side instruction. Omitting it silently costs
    retrieval quality — everything still works, just worse."""
    from ingest.embed import BGE_QUERY_PREFIX

    model = FakeSentenceModel()
    embedder = local(tmp_path, model)
    embedder.embed_texts(["a passage about charging"])
    embedder.embed_query("how do I charge it")
    assert not model.encoded[0][0].startswith(BGE_QUERY_PREFIX)
    assert model.encoded[1][0].startswith(BGE_QUERY_PREFIX)


def test_local_embedder_caches_like_the_remote_one(tmp_path):
    model = FakeSentenceModel()
    embedder = local(tmp_path, model)
    embedder.embed_texts(["alpha", "beta"])
    embedder.embed_texts(["alpha", "beta"])
    assert len(model.encoded) == 1  # second run encoded nothing


def test_local_cache_key_is_scoped_to_the_model(tmp_path):
    """Switching backends must not serve 384-dim vectors from a 768-dim run."""
    from ingest.embed import LOCAL_MODEL

    assert cache_key("t", LOCAL_MODEL, DOCUMENT_TASK, 384) != cache_key(
        "t", "gemini-embedding-001", DOCUMENT_TASK, 768
    )


def test_build_embedder_honours_the_configured_backend(monkeypatch):
    from core.config import load_settings
    from ingest.embed import GeminiEmbedder, LocalEmbedder, build_embedder

    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("EMBED_BACKEND", "local")
    assert isinstance(build_embedder(load_settings()), LocalEmbedder)
    monkeypatch.setenv("EMBED_BACKEND", "gemini")
    assert isinstance(build_embedder(load_settings()), GeminiEmbedder)


@pytest.mark.live
def test_live_local_model_dimension_and_asymmetry():
    from ingest.embed import LocalEmbedder

    embedder = LocalEmbedder()
    doc = embedder.embed_texts(["Wireless power sharing charges another device."])
    query = embedder.embed_query("how do I share my battery")
    assert doc.shape == (1, 384) and query.shape == (384,)
    assert not np.allclose(doc[0], query)


@pytest.mark.live
def test_self_retrieval_on_the_real_index():
    """Phase 3 exit gate: a chunk's own text must retrieve that exact text at
    rank 1 with a near-perfect score. If this fails, vectors and chunk ids have
    drifted apart and every citation downstream points at the wrong passage.

    The assertion is on *text*, not chunk id: 43% of the corpus is duplicated
    boilerplate — the same Google-settings passage appears in 22 manuals — so an
    identical passage legitimately comes back under a different id.
    """
    from core.config import load_settings
    from core.storage import Store
    from ingest.embed import LocalEmbedder

    settings = load_settings(require_api_key=False)
    embedder = LocalEmbedder(model_name=settings.local_embed_model)
    with Store(settings.store_dir) as store:
        sample = [c for batch in store.iter_chunks(400) for c in batch][::700][:6]
        assert sample, "no chunks in the store"
        for chunk in sample:
            vector = embedder.embed_texts([chunk.embed_text()])[0]
            hits = store.search_dense(vector, k=1)
            assert hits, f"chunk {chunk.chunk_id} retrieved nothing"
            assert hits[0].chunk.embed_text() == chunk.embed_text()
            assert hits[0].score == pytest.approx(1.0, abs=1e-3)
