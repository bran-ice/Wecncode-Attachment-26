from pathlib import Path

import pytest

from ingest.chunk import (
    MAX_TOKENS,
    _merge_small_siblings,
    _tail_overlap,
    chunk_document,
    estimate_tokens,
)
from ingest.parse import Block, ParsedDoc


def doc(*blocks: Block) -> ParsedDoc:
    return ParsedDoc(path=Path("Manual_EN.pdf"), blocks=list(blocks), n_pages=10)


def body(text, page=1, path="Getting started > Charging"):
    return Block(text, page, "body", 0, path)


def words(n: int, word="charge") -> str:
    return " ".join([word] * n)


def test_chunks_never_cross_a_section_boundary():
    """The rule the whole chunker exists to enforce: a spliced chunk answers
    neither section's question but ranks plausibly for both."""
    chunks = chunk_document(
        doc(
            body(words(400), 1, "Getting started > Charging"),
            body(words(400), 2, "Getting started > Wireless power sharing"),
        ),
        "d",
    )
    for chunk in chunks:
        assert chunk.section_path in {
            "Getting started > Charging",
            "Getting started > Wireless power sharing",
        }
    joined = {c.section_path for c in chunks}
    assert len(joined) == 2


def test_long_section_splits_with_overlap():
    chunks = chunk_document(doc(body(words(600) + " END", 1)), "d", target_tokens=200)
    assert len(chunks) > 1
    # Each continuation repeats the tail of its predecessor, so a procedure cut
    # across the boundary keeps its lead-in on both sides.
    assert chunks[1].text.split()[0] == "charge"


def test_small_siblings_merge_under_their_parent():
    """Samsung subsections are often one sentence; alone they make 30-token
    chunks with no context."""
    groups = [
        ("A > B > Turning off", [body("Press and hold the Side button.", 1, "A > B > Turning off")]),
        ("A > B > Forcing restart", [body("Hold for seven seconds.", 1, "A > B > Forcing restart")]),
        ("A > B > Emergency calls", [body("Tap Emergency call.", 1, "A > B > Emergency calls")]),
    ]
    merged = _merge_small_siblings(groups, target_tokens=500)
    assert len(merged) == 1
    assert merged[0][0] == "A > B"
    text = " ".join(b.text for b in merged[0][1])
    assert "Turning off:" in text and "Forcing restart:" in text


def test_merged_siblings_keep_their_own_headings_inline():
    """Merging must not lose which sub-topic each part describes."""
    groups = [
        ("A > B > Wired", [body("Use the cable.", 1, "A > B > Wired")]),
        ("A > B > Wireless", [body("Use the pad.", 1, "A > B > Wireless")]),
    ]
    merged = _merge_small_siblings(groups, target_tokens=500)
    texts = [b.text for b in merged[0][1]]
    assert "Wired:" in texts and "Wireless:" in texts


def test_sections_from_different_parents_never_merge():
    groups = [
        ("A > B > One", [body("short one", 1, "A > B > One")]),
        ("A > C > Two", [body("short two", 1, "A > C > Two")]),
    ]
    merged = _merge_small_siblings(groups, target_tokens=500)
    assert len(merged) == 2


def test_large_section_is_left_alone_by_merging():
    groups = [
        ("A > B > Big", [body(words(400), 1, "A > B > Big")]),
        ("A > B > Small", [body("tiny", 1, "A > B > Small")]),
    ]
    merged = _merge_small_siblings(groups, target_tokens=500)
    assert merged[0][0] == "A > B > Big"  # keeps its specific path


def test_page_range_is_accurate():
    chunks = chunk_document(
        doc(body("first page text here", 7), body("second page text here", 8)), "d"
    )
    assert (chunks[0].page_start, chunks[0].page_end) == (7, 8)


def test_tables_are_not_split_across_chunks():
    """Splitting a table strands its rows from the header row that names them."""
    table = Block(
        "| Button | Function |\n|---|---|\n" + "\n".join(f"| B{i} | does thing {i} |" for i in range(40)),
        3,
        "table",
        0,
        "A > B",
    )
    chunks = chunk_document(doc(body(words(300), 3, "A > B"), table), "d", target_tokens=350)
    holders = [c for c in chunks if "| Button | Function |" in c.text]
    assert len(holders) == 1
    assert holders[0].text.count("does thing") == 40


def test_no_chunk_exceeds_the_hard_ceiling():
    chunks = chunk_document(doc(body(words(3000), 1)), "d", target_tokens=400)
    assert all(c.token_count <= MAX_TOKENS * 1.3 for c in chunks)


def test_tiny_trailing_fragment_folds_into_the_previous_chunk():
    chunks = chunk_document(
        doc(body(words(300), 1, "A > B"), body("ok", 2, "A > B")), "d", target_tokens=250
    )
    assert all(c.token_count >= 20 for c in chunks)
    assert "ok" in chunks[-1].text


def test_headings_are_not_duplicated_into_chunk_text():
    """The path is prefixed at embed time; repeating it inline double-counts it."""
    chunks = chunk_document(
        doc(
            Block("Charging the battery", 1, "heading", 2, "A > Charging the battery"),
            body("Connect the cable.", 1, "A > Charging the battery"),
        ),
        "d",
    )
    assert chunks[0].text == "Connect the cable."


def test_doc_id_propagates():
    chunks = chunk_document(doc(body("some text about charging", 1)), "abc123")
    assert all(c.doc_id == "abc123" for c in chunks)


@pytest.mark.parametrize(
    "text,low,high",
    [("", 0, 1), ("one two three", 2, 6), (words(100), 100, 170)],
)
def test_token_estimate_is_in_the_right_ballpark(text, low, high):
    assert low <= estimate_tokens(text) <= high


def test_overlap_prefers_a_sentence_boundary():
    text = "First sentence here. Second sentence follows on. Third one ends it all."
    assert _tail_overlap(text, tokens=8).startswith(("Second", "Third"))


def test_empty_document_yields_no_chunks():
    assert chunk_document(doc(), "d") == []
