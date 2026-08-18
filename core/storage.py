"""The shared-storage contract.

The offline ingestion pipeline writes a store; the online query pipeline reads
one. They share nothing else, so this module is the whole interface between
them.

A store is a directory:

    data/store/
      corpus.db     SQLite: documents, chunks, chunks_fts (FTS5/BM25)
      index.faiss   FAISS IndexIDMap2 over IndexFlatIP; ids are chunk_ids

Writers must build through `staging_store()`, which assembles into a sibling
directory and swaps it into place only on success. A reader therefore never
observes a partially written store, and a crashed ingest leaves the previous
store serving.
"""

from __future__ import annotations

import re
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional, Sequence

import numpy as np

from core.logging_setup import get_logger
from core.schema import Chunk, Document, RetrievedChunk

log = get_logger(__name__)

DB_NAME = "corpus.db"
INDEX_NAME = "index.faiss"

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    doc_id      TEXT PRIMARY KEY,
    model       TEXT NOT NULL,
    title       TEXT NOT NULL,
    url         TEXT NOT NULL,
    sha256      TEXT NOT NULL,
    n_pages     INTEGER NOT NULL,
    language    TEXT NOT NULL DEFAULT 'en',
    region      TEXT,
    os_version  TEXT,
    ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id     INTEGER PRIMARY KEY,
    doc_id       TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    text         TEXT NOT NULL,
    section_path TEXT NOT NULL DEFAULT '',
    page_start   INTEGER NOT NULL,
    page_end     INTEGER NOT NULL,
    token_count  INTEGER NOT NULL DEFAULT 0,
    vector_id    INTEGER
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text,
    section_path,
    content='chunks',
    content_rowid='chunk_id',
    tokenize='porter unicode61'
);

-- Keep the FTS index in lockstep with `chunks`, so callers cannot forget.
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, text, section_path)
    VALUES (new.chunk_id, new.text, new.section_path);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text, section_path)
    VALUES ('delete', old.chunk_id, old.text, old.section_path);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text, section_path)
    VALUES ('delete', old.chunk_id, old.text, old.section_path);
    INSERT INTO chunks_fts(rowid, text, section_path)
    VALUES (new.chunk_id, new.text, new.section_path);
END;
"""


class StoreError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# Runs of word characters, keeping hyphens and dots that sit *inside* a token so
# part numbers ("EP-TA845") and versions ("6.1") survive as single terms.
_TERM_RE = re.compile(r"\w+(?:[-.]\w+)*", re.UNICODE)

# Terms are OR-joined for recall, which makes function words actively harmful:
# "how do I stop my phone from doing it" would match any long passage containing
# "phone" and "it", and long passages win on term frequency. Dropping them costs
# nothing — no manual is retrieved *because* it contains the word "the".
_STOPWORDS = frozenset("""
a an and are as at be been but by can can't cannot could did do does doing don't
for from get got had has have how i i'm if in into is it it's its just me my no
not of off on or our out over should so some that the their them then there these
they this to too was we were what when where which who why will with would you
your
""".split())


def fts_escape(query: str) -> str:
    """Turn free text into a safe FTS5 MATCH expression.

    Every term is quoted, so FTS5 operators in user input (`-`, `:`, `*`, `NEAR`,
    `"`) are treated as literal text. Terms are OR-ed: recall matters more than
    precision at this stage because fusion and reranking come after.
    """
    terms = _TERM_RE.findall(query or "")
    content = [t for t in terms if t.lower() not in _STOPWORDS]
    # If the query is nothing but function words, fall back to using them: an
    # empty MATCH expression returns nothing at all, which is worse.
    terms = content or terms
    if not terms:
        return ""
    return " OR ".join('"' + t.replace('"', '""') + '"' for t in terms)


class Store:
    """Read/write access to one store directory."""

    def __init__(self, root: Path, create: bool = False, multithread: bool = False):
        """`multithread` allows the connection to be used from more than one
        thread. Streamlit runs every rerun on a fresh thread while caching the
        Store across them, so without it the second interaction dies with
        *"SQLite objects created in a thread can only be used in that same
        thread"*. Safe only because the query pipeline never writes: SQLite
        serialises reads internally, and there is no write to interleave with.
        Ingestion must never set it — a half-applied write from two threads is
        exactly the corruption the atomic swap exists to prevent.
        """
        self.root = Path(root)
        if not self.root.exists():
            if not create:
                raise StoreError(
                    f"No store at {self.root}. Run `python -m ingest` to build one."
                )
            self.root.mkdir(parents=True, exist_ok=True)

        self.db_path = self.root / DB_NAME
        self.index_path = self.root / INDEX_NAME

        if not create and not self.db_path.exists():
            raise StoreError(f"Store at {self.root} has no {DB_NAME}.")

        if create and multithread:
            raise StoreError("multithread access is read-only; ingestion must not use it")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=not multithread)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        if create:
            self.conn.executescript(SCHEMA)
            self.conn.commit()

        self._index = None  # lazily loaded FAISS index

    # ---------------------------------------------------------------- meta

    def set_meta(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        self.conn.commit()

    def get_meta(self, key: str, default: Optional[str] = None) -> Optional[str]:
        row = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    # ----------------------------------------------------------- documents

    def add_document(self, doc: Document) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO documents
               (doc_id, model, title, url, sha256, n_pages, language, region,
                os_version, ingested_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                doc.doc_id,
                doc.model,
                doc.title,
                doc.url,
                doc.sha256,
                doc.n_pages,
                doc.language,
                doc.region,
                doc.os_version,
                doc.ingested_at or _now(),
            ),
        )
        self.conn.commit()

    def get_document(self, doc_id: str) -> Optional[Document]:
        row = self.conn.execute(
            "SELECT * FROM documents WHERE doc_id=?", (doc_id,)
        ).fetchone()
        return _row_to_document(row) if row else None

    def list_documents(self) -> list[Document]:
        rows = self.conn.execute("SELECT * FROM documents ORDER BY model").fetchall()
        return [_row_to_document(r) for r in rows]

    def has_document(self, sha256: str) -> bool:
        return (
            self.conn.execute(
                "SELECT 1 FROM documents WHERE sha256=?", (sha256,)
            ).fetchone()
            is not None
        )

    # -------------------------------------------------------------- chunks

    def add_chunks(self, chunks: Sequence[Chunk]) -> list[int]:
        """Insert chunks, assigning `chunk_id` in place. Returns the new ids."""
        ids: list[int] = []
        cur = self.conn.cursor()
        for c in chunks:
            cur.execute(
                """INSERT INTO chunks
                   (doc_id, text, section_path, page_start, page_end, token_count)
                   VALUES (?,?,?,?,?,?)""",
                (
                    c.doc_id,
                    c.text,
                    c.section_path,
                    c.page_start,
                    c.page_end,
                    c.token_count,
                ),
            )
            c.chunk_id = int(cur.lastrowid)
            ids.append(c.chunk_id)
        self.conn.commit()
        return ids

    def get_chunk(self, chunk_id: int) -> Optional[Chunk]:
        row = self.conn.execute(
            "SELECT * FROM chunks WHERE chunk_id=?", (chunk_id,)
        ).fetchone()
        return _row_to_chunk(row) if row else None

    def get_chunks(self, chunk_ids: Sequence[int]) -> list[Chunk]:
        """Fetch many chunks, preserving the caller's ordering (i.e. rank order)."""
        if not chunk_ids:
            return []
        placeholders = ",".join("?" * len(chunk_ids))
        rows = self.conn.execute(
            f"SELECT * FROM chunks WHERE chunk_id IN ({placeholders})",
            tuple(chunk_ids),
        ).fetchall()
        by_id = {r["chunk_id"]: _row_to_chunk(r) for r in rows}
        return [by_id[i] for i in chunk_ids if i in by_id]

    def iter_chunks(self, batch_size: int = 500) -> Iterator[list[Chunk]]:
        cur = self.conn.execute("SELECT * FROM chunks ORDER BY chunk_id")
        while rows := cur.fetchmany(batch_size):
            yield [_row_to_chunk(r) for r in rows]

    def count_chunks(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])

    # -------------------------------------------------------------- search

    def search_bm25(self, query: str, k: int = 30) -> list[RetrievedChunk]:
        """Keyword search over natural-language input.

        The query is escaped, not passed through: FTS5 would read `EP-TA845` as
        a NOT operator and `Settings:` as a column filter, so raw user text
        silently matches nothing. Scores are negated so higher is better.
        """
        match = fts_escape(query)
        if not match:
            return []
        try:
            rows = self.conn.execute(
                """SELECT c.*, bm25(chunks_fts) AS score
                   FROM chunks_fts
                   JOIN chunks c ON c.chunk_id = chunks_fts.rowid
                   WHERE chunks_fts MATCH ?
                   ORDER BY score
                   LIMIT ?""",
                (match, k),
            ).fetchall()
        except sqlite3.OperationalError as exc:
            # Escaping should make this unreachable; keep it so a surprising
            # query degrades to "no keyword hits" instead of killing the turn.
            log.warning("FTS query rejected (%s): %r", exc, match)
            return []

        return [
            RetrievedChunk(
                chunk=_row_to_chunk(r), score=-float(r["score"]), source="bm25", rank=i
            )
            for i, r in enumerate(rows)
        ]

    def search_dense(self, vector: np.ndarray, k: int = 30) -> list[RetrievedChunk]:
        """Cosine search over the FAISS index (vectors are stored normalized)."""
        index = self.index
        if index is None or index.ntotal == 0:
            return []
        q = np.asarray(vector, dtype="float32").reshape(1, -1)
        q = q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-12)
        scores, ids = index.search(q, min(k, index.ntotal))

        hits = [(int(i), float(s)) for i, s in zip(ids[0], scores[0]) if i != -1]
        chunks = {c.chunk_id: c for c in self.get_chunks([i for i, _ in hits])}
        return [
            RetrievedChunk(chunk=chunks[i], score=s, source="dense", rank=rank)
            for rank, (i, s) in enumerate(hits)
            if i in chunks
        ]

    # --------------------------------------------------------- vector index

    @property
    def index(self):
        if self._index is None and self.index_path.exists():
            import faiss

            self._index = faiss.read_index(str(self.index_path))
        return self._index

    def build_vector_index(self, chunk_ids: Sequence[int], vectors: np.ndarray) -> None:
        """Write the FAISS index. Vectors are L2-normalized here, once."""
        import faiss

        if len(chunk_ids) != len(vectors):
            raise StoreError(
                f"{len(chunk_ids)} ids but {len(vectors)} vectors — refusing to build "
                "an index whose ids would be misaligned."
            )
        if not len(chunk_ids):
            raise StoreError("Refusing to build an empty index.")

        mat = np.asarray(vectors, dtype="float32")
        mat = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12)

        dim = mat.shape[1]
        index = faiss.IndexIDMap2(faiss.IndexFlatIP(dim))
        index.add_with_ids(mat, np.asarray(chunk_ids, dtype="int64"))
        faiss.write_index(index, str(self.index_path))
        self._index = index

        self.conn.executemany(
            "UPDATE chunks SET vector_id=? WHERE chunk_id=?",
            [(int(i), int(i)) for i in chunk_ids],
        )
        self.conn.commit()
        self.set_meta("embed_dim", str(dim))
        self.set_meta("indexed_at", _now())
        log.info("Built index: %d vectors, dim %d", len(chunk_ids), dim)

    # --------------------------------------------------------------- close

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def _row_to_document(row: sqlite3.Row) -> Document:
    return Document(
        doc_id=row["doc_id"],
        model=row["model"],
        title=row["title"],
        url=row["url"],
        sha256=row["sha256"],
        n_pages=row["n_pages"],
        language=row["language"],
        region=row["region"],
        os_version=row["os_version"],
        ingested_at=row["ingested_at"],
    )


def _row_to_chunk(row: sqlite3.Row) -> Chunk:
    return Chunk(
        chunk_id=row["chunk_id"],
        doc_id=row["doc_id"],
        text=row["text"],
        section_path=row["section_path"],
        page_start=row["page_start"],
        page_end=row["page_end"],
        token_count=row["token_count"],
        vector_id=row["vector_id"],
    )


@contextmanager
def staging_store(root: Path) -> Iterator[Store]:
    """Build a store off to the side; swap it in only if the block succeeds.

    On any exception the staging directory is discarded and whatever was at
    `root` is left untouched — which is the property the online pipeline relies
    on to never read a half-built index.
    """
    root = Path(root)
    staging = root.with_name(root.name + ".new")
    backup = root.with_name(root.name + ".old")

    for path in (staging, backup):
        if path.exists():
            shutil.rmtree(path)

    store = Store(staging, create=True)
    try:
        yield store
    except BaseException:
        store.close()
        shutil.rmtree(staging, ignore_errors=True)
        raise
    store.close()

    # Windows cannot rename onto an existing directory, so: move the live store
    # aside, move staging into place, then drop the old one.
    root.parent.mkdir(parents=True, exist_ok=True)
    had_previous = root.exists()
    if had_previous:
        root.rename(backup)
    try:
        staging.rename(root)
    except BaseException:
        if had_previous:
            backup.rename(root)  # put the working store back
        shutil.rmtree(staging, ignore_errors=True)
        raise
    if had_previous:
        shutil.rmtree(backup, ignore_errors=True)
    log.info("Store committed: %s", root)
