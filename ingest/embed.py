"""Turn chunk text into vectors via Gemini, cheaply and resumably.

Three properties matter more than speed here:

* **Never pay twice.** Vectors are cached by a hash of exactly what was sent
  (text + model + task type + dimensionality). Re-running after a chunking tweak
  re-embeds only what actually changed, which during Phase 4 tuning is the
  difference between a free re-index and a paid one.
* **Survive a crash.** The cache is written as each batch returns, so an
  interrupted run resumes instead of starting over.
* **Ask the right question.** Gemini distinguishes `RETRIEVAL_DOCUMENT` (what is
  this passage about?) from `RETRIEVAL_QUERY` (what is this person looking for?).
  Embedding a query as a document quietly degrades every search.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import time
from collections import deque
from pathlib import Path
from typing import Iterable, Optional, Sequence

import numpy as np

from core.logging_setup import get_logger

log = get_logger(__name__)

EMBED_DIM = 768  # 3072 is the default; 768 is 4x smaller with negligible quality loss
BATCH_SIZE = 45  # must divide ITEMS_PER_MINUTE — see test
MAX_RETRIES = 8

# The free tier allows 100 *items* per minute, not 100 requests — a batch of 50
# spends 50 of them. Pacing below the limit is far better than discovering it by
# being rejected: a 429 wastes the whole batch and the backoff that follows.
ITEMS_PER_MINUTE = 90
_RETRY_DELAY_RE = re.compile(r"retryDelay['\"]?:\s*['\"]?(\d+(?:\.\d+)?)s")


class RateLimiter:
    """Sliding-window limiter over the last 60 seconds."""

    def __init__(self, per_minute: int = ITEMS_PER_MINUTE, sleep=time.sleep, clock=time.monotonic):
        self.per_minute = per_minute
        self._sleep = sleep
        self._clock = clock
        self._events: deque[tuple[float, int]] = deque()  # (when, how many)

    def _spent(self) -> int:
        cutoff = self._clock() - 60.0
        while self._events and self._events[0][0] <= cutoff:
            self._events.popleft()
        return sum(count for _, count in self._events)

    def acquire(self, items: int) -> None:
        while self._events and self._spent() + items > self.per_minute:
            wait = 60.0 - (self._clock() - self._events[0][0]) + 0.1
            if wait <= 0:
                break
            log.info("Rate limit: waiting %.0fs for quota", wait)
            self._sleep(wait)
        self._events.append((self._clock(), items))


DOCUMENT_TASK = "RETRIEVAL_DOCUMENT"
QUERY_TASK = "RETRIEVAL_QUERY"


class EmbeddingError(RuntimeError):
    pass


def cache_key(text: str, model: str, task_type: str, dim: int) -> str:
    payload = f"{model}\x00{task_type}\x00{dim}\x00{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class EmbeddingCache:
    """Content-addressed vector store on disk.

    Deliberately kept *outside* `data/store/`: that directory is swapped whole on
    every re-index, and a cache living inside it would be deleted exactly when it
    is most valuable.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS vectors ("
            "  key TEXT PRIMARY KEY, dim INTEGER NOT NULL, vec BLOB NOT NULL)"
        )
        self.conn.commit()

    def get_many(self, keys: Sequence[str]) -> dict[str, np.ndarray]:
        found: dict[str, np.ndarray] = {}
        for start in range(0, len(keys), 500):  # SQLite caps bound parameters
            window = keys[start : start + 500]
            placeholders = ",".join("?" * len(window))
            for key, dim, blob in self.conn.execute(
                f"SELECT key, dim, vec FROM vectors WHERE key IN ({placeholders})",
                tuple(window),
            ):
                found[key] = np.frombuffer(blob, dtype="float32").reshape(dim)
        return found

    def put_many(self, items: Iterable[tuple[str, np.ndarray]]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO vectors(key, dim, vec) VALUES (?,?,?)",
            [
                (key, int(vec.shape[0]), np.asarray(vec, dtype="float32").tobytes())
                for key, vec in items
            ],
        )
        self.conn.commit()

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM vectors").fetchone()[0])

    def close(self) -> None:
        self.conn.close()


class GeminiEmbedder:
    """Batched Gemini embeddings with retry, backoff and caching."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-embedding-001",
        dim: int = EMBED_DIM,
        cache: Optional[EmbeddingCache] = None,
        client=None,
        sleep=time.sleep,
        limiter: Optional[RateLimiter] = None,
    ):
        self.model = model
        self.dim = dim
        self.cache = cache
        self._sleep = sleep
        self._client = client
        self._api_key = api_key
        self.limiter = limiter if limiter is not None else RateLimiter(sleep=sleep)
        self.api_calls = 0
        self.cached_hits = 0

    @property
    def client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def _call(self, texts: Sequence[str], task_type: str) -> list[np.ndarray]:
        from google.genai import types

        config = types.EmbedContentConfig(
            task_type=task_type, output_dimensionality=self.dim
        )
        delay = 5.0
        for attempt in range(MAX_RETRIES):
            try:
                self.limiter.acquire(len(texts))
                response = self.client.models.embed_content(
                    model=self.model, contents=list(texts), config=config
                )
                self.api_calls += 1
                return [
                    np.asarray(e.values, dtype="float32") for e in response.embeddings
                ]
            except Exception as exc:
                message = str(exc)
                retryable = any(
                    token in message
                    for token in ("429", "RESOURCE_EXHAUSTED", "503", "500", "UNAVAILABLE", "timeout")
                )
                if not retryable or attempt == MAX_RETRIES - 1:
                    raise EmbeddingError(f"embedding failed: {message}") from exc
                # Gemini tells us how long to wait; trust it over our guess.
                if hint := _RETRY_DELAY_RE.search(message):
                    delay = max(delay, float(hint.group(1)) + 2.0)
                log.warning(
                    "Embedding batch failed (%s); retrying in %.0fs", message[:80], delay
                )
                self._sleep(delay)
                delay = min(delay * 2, 90.0)
        raise EmbeddingError("unreachable")

    def embed_texts(
        self, texts: Sequence[str], task_type: str = DOCUMENT_TASK,
        batch_size: int = BATCH_SIZE, progress_every: int = 10,
    ) -> np.ndarray:
        """Embed many texts, in order. Cached entries cost nothing."""
        if not texts:
            return np.zeros((0, self.dim), dtype="float32")

        keys = [cache_key(t, self.model, task_type, self.dim) for t in texts]
        known: dict[str, np.ndarray] = (
            self.cache.get_many(keys) if self.cache else {}
        )
        self.cached_hits += sum(1 for k in keys if k in known)

        # De-duplicate: manuals repeat boilerplate verbatim across models, so the
        # same passage can appear a dozen times in one corpus.
        pending: dict[str, str] = {}
        for key, text in zip(keys, texts):
            if key not in known and key not in pending:
                pending[key] = text

        if pending:
            log.info(
                "Embedding %d new passages (%d already cached, %d duplicates collapsed)",
                len(pending),
                len(known),
                len(texts) - len(set(keys)),
            )

        pending_keys = list(pending)
        for start in range(0, len(pending_keys), batch_size):
            window = pending_keys[start : start + batch_size]
            vectors = self._call([pending[k] for k in window], task_type)
            if len(vectors) != len(window):
                raise EmbeddingError(
                    f"asked for {len(window)} embeddings, got {len(vectors)} — "
                    "refusing to misalign vectors with chunks"
                )
            pairs = list(zip(window, vectors))
            known.update(pairs)
            if self.cache:
                self.cache.put_many(pairs)  # checkpoint every batch
            done = start + len(window)
            if progress_every and (start // batch_size) % progress_every == 0:
                log.info("  embedded %d/%d", done, len(pending_keys))

        return np.vstack([known[k] for k in keys])

    def embed_query(self, text: str) -> np.ndarray:
        """Embed a user question. Note the different task type."""
        return self.embed_texts([text], task_type=QUERY_TASK, progress_every=0)[0]


LOCAL_MODEL = "BAAI/bge-small-en-v1.5"
LOCAL_DIM = 384

# BGE models are trained with an instruction prefix on the *query* side only.
# Omitting it costs several points of retrieval quality, and the failure is
# silent — everything still returns results, just worse ones.
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class LocalEmbedder:
    """Sentence-transformers embeddings, computed on this machine.

    Same interface as `GeminiEmbedder` so the pipeline neither knows nor cares
    which is in use. Chosen here because Gemini's free tier caps embeddings at
    1,000 items per day and the corpus needs 4,630 — five days of waiting, or
    five minutes of local CPU.

    Query/document asymmetry is preserved: BGE expects an instruction prefix on
    queries, which is this model's equivalent of Gemini's task types.
    """

    def __init__(
        self,
        model_name: str = LOCAL_MODEL,
        cache: Optional[EmbeddingCache] = None,
        model=None,
        batch_size: int = 64,
    ):
        self.model_name = model_name
        self.cache = cache
        self._model = model
        self.batch_size = batch_size
        self.dim = LOCAL_DIM
        self.api_calls = 0
        self.cached_hits = 0

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            log.info("Loading %s (first run downloads ~130MB)", self.model_name)
            self._model = SentenceTransformer(self.model_name)
            self.dim = self._model.get_sentence_embedding_dimension()
        return self._model

    def embed_texts(
        self, texts: Sequence[str], task_type: str = DOCUMENT_TASK,
        batch_size: Optional[int] = None, progress_every: int = 10,
    ) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype="float32")

        keys = [cache_key(t, self.model_name, task_type, self.dim) for t in texts]
        known: dict[str, np.ndarray] = self.cache.get_many(keys) if self.cache else {}
        self.cached_hits += sum(1 for k in keys if k in known)

        pending: dict[str, str] = {}
        for key, text in zip(keys, texts):
            if key not in known and key not in pending:
                pending[key] = text

        if pending:
            log.info(
                "Embedding %d passages locally (%d cached, %d duplicates collapsed)",
                len(pending), len(known), len(texts) - len(set(keys)),
            )
            pending_keys = list(pending)
            prepared = [
                BGE_QUERY_PREFIX + pending[k] if task_type == QUERY_TASK else pending[k]
                for k in pending_keys
            ]
            vectors = self.model.encode(
                prepared,
                batch_size=batch_size or self.batch_size,
                show_progress_bar=False,
                normalize_embeddings=False,  # storage normalizes once, at index build
                convert_to_numpy=True,
            ).astype("float32")
            self.api_calls += 1
            pairs = list(zip(pending_keys, vectors))
            known.update(pairs)
            if self.cache:
                self.cache.put_many(pairs)

        return np.vstack([known[k] for k in keys])

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_texts([text], task_type=QUERY_TASK, progress_every=0)[0]


def build_embedder(settings, cache: Optional[EmbeddingCache] = None):
    """Pick an embedder from settings. The pipeline stays backend-agnostic."""
    if settings.embed_backend == "gemini":
        return GeminiEmbedder(
            api_key=settings.gemini_api_key,
            model=settings.embed_model,
            dim=EMBED_DIM,
            cache=cache,
        )
    return LocalEmbedder(model_name=settings.local_embed_model, cache=cache)
