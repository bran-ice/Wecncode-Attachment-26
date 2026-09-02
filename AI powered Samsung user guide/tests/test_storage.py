"""Phase 0 gate: a document survives a round trip, and a crashed write cannot
corrupt a live store."""

import numpy as np
import pytest

from core.storage import Store, StoreError, staging_store


def _make_store(tmp_path, doc, chunks) -> Store:
    store = Store(tmp_path / "store", create=True)
    store.add_document(doc)
    store.add_chunks(chunks)
    return store


def test_storage_roundtrip(tmp_path, doc, chunks):
    store = _make_store(tmp_path, doc, chunks)
    store.close()

    with Store(tmp_path / "store") as reopened:
        got_doc = reopened.get_document(doc.doc_id)
        assert got_doc.model == "Galaxy S24 Ultra"
        assert got_doc.n_pages == 180
        assert got_doc.os_version == "One UI 6.1"
        assert reopened.count_chunks() == 3

        first = reopened.get_chunk(chunks[0].chunk_id)
        assert first.text == chunks[0].text
        assert first.section_path == "Settings > Lock screen"
        assert (first.page_start, first.page_end) == (42, 42)


def test_fts_populated_by_trigger(tmp_path, doc, chunks):
    """Callers never touch chunks_fts; the trigger must keep it in sync."""
    store = _make_store(tmp_path, doc, chunks)
    hits = store.search_bm25("Always On Display")
    assert hits, "inserted chunk was not findable via FTS5"
    assert hits[0].chunk.chunk_id == chunks[0].chunk_id
    assert hits[0].source == "bm25"
    store.close()


def test_fts_finds_exact_part_number(tmp_path, doc, chunks):
    """The reason BM25 is in the system at all: verbatim codes."""
    store = _make_store(tmp_path, doc, chunks)
    hits = store.search_bm25("EP-TA845")
    assert [h.chunk.chunk_id for h in hits][:1] == [chunks[1].chunk_id]
    store.close()


def test_fts_reflects_delete(tmp_path, doc, chunks):
    store = _make_store(tmp_path, doc, chunks)
    store.conn.execute("DELETE FROM chunks WHERE chunk_id=?", (chunks[0].chunk_id,))
    store.conn.commit()
    hits = store.search_bm25("Always On Display")
    assert chunks[0].chunk_id not in [h.chunk.chunk_id for h in hits]
    store.close()


def test_fts_survives_operator_characters_in_user_text(tmp_path, doc, chunks):
    """FTS5 syntax in natural input must be literal text, not operators."""
    store = _make_store(tmp_path, doc, chunks)
    for query in [
        'unbalanced "quote',
        "Settings: Lock screen",
        "adapter -EP",
        "charging NEAR adapter",
        "45W*",
    ]:
        store.search_bm25(query)  # must not raise
    assert store.search_bm25("Settings: Lock screen")
    store.close()


def test_empty_and_punctuation_only_queries_return_empty(tmp_path, doc, chunks):
    store = _make_store(tmp_path, doc, chunks)
    assert store.search_bm25("") == []
    assert store.search_bm25("   ") == []
    assert store.search_bm25("?!--") == []
    store.close()


def test_fts_escape_quotes_every_term():
    from core.storage import fts_escape

    assert fts_escape("EP-TA845") == '"EP-TA845"'
    assert fts_escape("fast charging") == '"fast" OR "charging"'
    assert fts_escape('say "hi"') == '"say" OR "hi"'
    assert fts_escape("One UI 6.1") == '"One" OR "UI" OR "6.1"'
    assert fts_escape("---") == ""


def test_vector_id_mapping_survives_save_load(tmp_path, doc, chunks):
    store = _make_store(tmp_path, doc, chunks)
    ids = [c.chunk_id for c in chunks]
    vectors = np.eye(3, 8, dtype="float32")  # orthogonal, so nearest is unambiguous
    store.build_vector_index(ids, vectors)
    store.close()

    with Store(tmp_path / "store") as reopened:
        assert reopened.get_meta("embed_dim") == "8"
        for i, chunk_id in enumerate(ids):
            hits = reopened.search_dense(vectors[i], k=1)
            assert hits[0].chunk.chunk_id == chunk_id
            assert hits[0].chunk.vector_id == chunk_id
            assert hits[0].score == pytest.approx(1.0, abs=1e-5)


def test_vectors_are_normalized_on_write(tmp_path, doc, chunks):
    store = _make_store(tmp_path, doc, chunks)
    ids = [c.chunk_id for c in chunks]
    store.build_vector_index(ids, np.eye(3, 8, dtype="float32") * 17.0)
    # Un-normalized input must still yield cosine scores in [-1, 1].
    hit = store.search_dense(np.eye(3, 8, dtype="float32")[0] * 4.0, k=1)[0]
    assert hit.score == pytest.approx(1.0, abs=1e-5)
    store.close()


def test_misaligned_ids_and_vectors_rejected(tmp_path, doc, chunks):
    store = _make_store(tmp_path, doc, chunks)
    with pytest.raises(StoreError, match="misaligned"):
        store.build_vector_index([c.chunk_id for c in chunks], np.eye(2, 8))
    store.close()


def test_get_chunks_preserves_rank_order(tmp_path, doc, chunks):
    store = _make_store(tmp_path, doc, chunks)
    wanted = [chunks[2].chunk_id, chunks[0].chunk_id]
    assert [c.chunk_id for c in store.get_chunks(wanted)] == wanted
    store.close()


def test_opening_missing_store_is_a_clear_error(tmp_path):
    with pytest.raises(StoreError, match="python -m ingest"):
        Store(tmp_path / "nope")


# ------------------------------------------------------------------ atomicity


def test_staging_commit_replaces_previous_store(tmp_path, doc, chunks):
    root = tmp_path / "store"
    with staging_store(root) as s:
        s.add_document(doc)
        s.add_chunks(chunks)
    assert root.exists()

    with staging_store(root) as s:
        s.add_document(doc)
        s.add_chunks(chunks[:1])

    with Store(root) as reopened:
        assert reopened.count_chunks() == 1
    assert not root.with_name("store.new").exists()
    assert not root.with_name("store.old").exists()


def test_crash_mid_write_leaves_previous_store_intact(tmp_path, doc, chunks):
    """The property the online pipeline depends on."""
    root = tmp_path / "store"
    with staging_store(root) as s:
        s.add_document(doc)
        s.add_chunks(chunks)

    with pytest.raises(RuntimeError, match="boom"):
        with staging_store(root) as s:
            s.add_document(doc)
            raise RuntimeError("boom")

    with Store(root) as reopened:
        assert reopened.count_chunks() == 3  # still the good store
        assert reopened.search_bm25("Always On Display")
    assert not root.with_name("store.new").exists()


def test_crash_on_first_ever_build_leaves_no_store(tmp_path, doc):
    root = tmp_path / "store"
    with pytest.raises(RuntimeError):
        with staging_store(root) as s:
            s.add_document(doc)
            raise RuntimeError("boom")
    assert not root.exists()
    assert not root.with_name("store.new").exists()


def test_stopwords_are_dropped_from_fts_queries():
    """Terms are OR-joined, so function words are actively harmful: "how do I
    stop my phone from doing it" matched any long passage containing "phone"
    and "it". On the real corpus this made one Reminder passage the top hit for
    several unrelated questions; removing stopwords lifted recall@5 from 0.68
    to 0.91 and cut p50 latency from 240ms to 57ms."""
    from core.storage import fts_escape

    assert fts_escape("what happens if I lose my phone") == '"happens" OR "lose" OR "phone"'
    assert fts_escape("how do I make it charge faster") == '"make" OR "charge" OR "faster"'


def test_stopword_only_query_falls_back_rather_than_matching_nothing():
    from core.storage import fts_escape

    assert fts_escape("how do I do it") != ""


def test_part_numbers_survive_stopword_filtering():
    from core.storage import fts_escape

    assert fts_escape("is the EP-TA845 in the box") == '"EP-TA845" OR "box"'


def test_multithread_store_is_readable_from_another_thread(tmp_path, doc, chunks):
    """Streamlit caches one Store and reruns on a new thread each time."""
    import threading

    with staging_store(tmp_path / "store") as store:
        store.add_document(doc)
        store.add_chunks(chunks)

    reader = Store(tmp_path / "store", multithread=True)
    result = {}

    def read():
        result["n"] = reader.count_chunks()

    thread = threading.Thread(target=read)
    thread.start()
    thread.join()
    reader.close()
    assert result["n"] == len(chunks)


def test_multithread_is_refused_for_writes(tmp_path):
    """Ingestion must never open a cross-thread connection."""
    with pytest.raises(StoreError, match="read-only"):
        Store(tmp_path / "new", create=True, multithread=True)
