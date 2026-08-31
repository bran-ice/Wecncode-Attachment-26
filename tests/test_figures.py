"""Figures: detection thresholds, chunk association, storage, and rendering gate.

The detector's thresholds are the interesting part. Each test here names the
failure the corresponding rule prevents, because the rules look arbitrary until
you have seen what the corpus does without them — see `ingest/figures.py`.

Detection runs against synthesised PDFs rather than the shipped excerpts: the
excerpts carry three figures total and no outline, which is too thin to pin
behaviour on, and a placeholder corpus is exactly what should not be baked into
assertions.
"""

from __future__ import annotations

import pytest

from core.schema import Answer, Chunk, Citation, Figure
from core.storage import Store
from ingest.chunk import chunk_document
from ingest.figures import (
    MAX_WORDS_INSIDE,
    MIN_PT,
    RenderedFigure,
    detect_figures,
    figure_out_dir,
    figure_rel_path,
    render_figure,
)
from ingest.parse import Block, ParsedDoc

pymupdf = pytest.importorskip("pymupdf")


# --- helpers --------------------------------------------------------------


def _page(build):
    """A one-page document whose page `build` has drawn on."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4
    build(page)
    return doc, page


def _figure_block(page=5, filename="deadbeef.png", width=200, height=400) -> Block:
    return Block(
        "", page, "figure", 0, "Camera > Taking pictures",
        figure=RenderedFigure(page=page, filename=filename, width=width, height=height),
    )


def _body(text, page=5, section="Camera > Taking pictures") -> Block:
    return Block(text, page, "body", 0, section)


# --- detection thresholds -------------------------------------------------


def test_inline_icons_are_not_figures():
    """Most raster XObjects in these manuals are 16x16 status-bar glyphs."""
    def build(page):
        page.draw_rect(pymupdf.Rect(100, 100, 116, 116), fill=(0, 0, 0))

    doc, page = _page(build)
    assert detect_figures(page) == []
    doc.close()


def test_full_page_background_is_not_a_figure():
    """Unioning every large path once reported a whole page as one figure."""
    def build(page):
        page.draw_rect(page.rect, fill=(0.9, 0.9, 0.9))

    doc, page = _page(build)
    assert detect_figures(page) == []
    doc.close()


def test_an_illustration_is_detected():
    def build(page):
        page.draw_circle(pymupdf.Point(200, 200), 60, fill=(0, 0, 1))

    doc, page = _page(build)
    found = detect_figures(page)
    assert len(found) == 1
    assert found[0].page == 1
    assert found[0].bbox[2] - found[0].bbox[0] >= MIN_PT
    doc.close()


def test_nearby_shapes_become_one_figure():
    """A figure arrives as many paths; ungrouped it becomes a dozen slivers."""
    def build(page):
        page.draw_circle(pymupdf.Point(200, 200), 40, fill=(0, 0, 1))
        page.draw_circle(pymupdf.Point(250, 200), 40, fill=(1, 0, 0))

    doc, page = _page(build)
    assert len(detect_figures(page)) == 1
    doc.close()


def test_distant_shapes_stay_separate():
    def build(page):
        page.draw_circle(pymupdf.Point(150, 150), 40, fill=(0, 0, 1))
        page.draw_circle(pymupdf.Point(450, 700), 40, fill=(1, 0, 0))

    doc, page = _page(build)
    assert len(detect_figures(page)) == 2
    doc.close()


def test_a_region_full_of_prose_is_not_a_figure():
    """A boxed note is page furniture, not an illustration."""
    def build(page):
        page.draw_rect(pymupdf.Rect(80, 80, 500, 400))
        words = " ".join(["word"] * (MAX_WORDS_INSIDE + 20))
        page.insert_textbox(pymupdf.Rect(90, 90, 490, 390), words, fontsize=9)

    doc, page = _page(build)
    assert detect_figures(page) == []
    doc.close()


def test_figures_come_back_in_reading_order():
    def build(page):
        page.draw_circle(pymupdf.Point(300, 600), 40, fill=(0, 0, 1))
        page.draw_circle(pymupdf.Point(300, 150), 40, fill=(1, 0, 0))

    doc, page = _page(build)
    found = detect_figures(page)
    assert [round(f.top) for f in found] == sorted(round(f.top) for f in found)
    doc.close()


# --- rendering ------------------------------------------------------------


def test_render_is_content_addressed(tmp_path):
    """Identical bytes get one file: these manuals reuse a diagram heavily."""
    def build(page):
        page.draw_circle(pymupdf.Point(200, 200), 60, fill=(0, 0, 1))

    doc, page = _page(build)
    found = detect_figures(page)
    first = render_figure(page, found[0], tmp_path)
    second = render_figure(page, found[0], tmp_path)

    assert first.filename == second.filename
    assert len(list(tmp_path.glob("*.png"))) == 1
    assert (tmp_path / first.filename).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    doc.close()


def test_render_captures_vector_overlay_not_just_the_raster(tmp_path):
    """The reason regions are rendered rather than images extracted.

    Samsung draws callout lines over a raster screenshot; extracting the
    embedded image alone loses the annotation. A region render composites both,
    so a page whose *only* content is vector art still yields a figure — which
    an XObject-extraction approach would miss entirely.
    """
    def build(page):
        page.draw_circle(pymupdf.Point(200, 200), 60, fill=(0, 0, 1))
        page.draw_line(pymupdf.Point(200, 200), pymupdf.Point(240, 240))

    doc, page = _page(build)
    assert page.get_images(full=True) == []  # nothing to extract
    rendered = render_figure(page, detect_figures(page)[0], tmp_path)
    assert rendered is not None and rendered.width > 0
    doc.close()


def test_path_helpers_agree(tmp_path):
    """The writer builds a directory and the reader resolves a string; a
    mismatch shows up only as a broken image."""
    out = figure_out_dir(tmp_path, "doc123")
    rel = figure_rel_path("doc123", "abc.png")
    assert (out / "abc.png") == tmp_path / rel


# --- chunk association ----------------------------------------------------


def _parsed(blocks) -> ParsedDoc:
    return ParsedDoc(path=type("P", (), {"name": "m.pdf"})(), blocks=blocks)


def test_figure_attaches_to_the_surrounding_chunk():
    blocks = [_body("Open the Camera app and tap the shutter button. " * 5),
              _figure_block(),
              _body("Tap the zoom icon to change the zoom level. " * 5)]
    chunks = chunk_document(_parsed(blocks), doc_id="d1")
    with_figures = [c for c in chunks if c.figures]
    assert with_figures, "the figure must land on a chunk"
    assert with_figures[0].figures[0].rel_path == figure_rel_path("d1", "deadbeef.png")


def test_a_figure_adds_no_text_and_no_tokens():
    """A figure is a position in reading order, nothing more. If it leaked into
    the text it would also leak into the embedding and perturb ranking."""
    text_only = chunk_document(_parsed([_body("Open the Camera app. " * 20)]), "d1")
    with_figure = chunk_document(
        _parsed([_body("Open the Camera app. " * 20), _figure_block()]), "d1"
    )
    assert [c.text for c in with_figure] == [c.text for c in text_only]
    assert [c.token_count for c in with_figure] == [c.token_count for c in text_only]


def test_figures_are_not_in_embed_text():
    chunk = Chunk(
        doc_id="d1", text="Tap the shutter button.", page_start=1, page_end=1,
        section_path="Camera",
        figures=[Figure(doc_id="d1", page=1, rel_path="figures/d1/a.png",
                        width=10, height=10)],
    )
    assert "a.png" not in chunk.embed_text()
    assert "figures" not in chunk.embed_text()


def test_a_figure_with_no_prose_is_dropped():
    """Nothing to illustrate, so it must not drift onto an unrelated chunk."""
    chunks = chunk_document(_parsed([_figure_block()]), doc_id="d1")
    assert all(not c.figures for c in chunks)


# --- storage --------------------------------------------------------------


@pytest.fixture
def store(tmp_path, doc):
    s = Store(tmp_path / "store", create=True)
    s.add_document(doc)
    return s


def _chunk_with(doc, figures, text="Tap the shutter button to take a photo.") -> Chunk:
    return Chunk(
        doc_id=doc.doc_id, text=text, page_start=10, page_end=10,
        section_path="Camera", figures=figures,
    )


def test_figures_round_trip(store, doc):
    figure = Figure(doc_id=doc.doc_id, page=10,
                    rel_path=figure_rel_path(doc.doc_id, "a.png"),
                    width=237, height=496)
    chunk = _chunk_with(doc, [figure])
    store.add_chunks([chunk])
    assert store.add_chunk_figures([chunk]) == 1

    back = store.get_figures(chunk.chunk_id)
    assert len(back) == 1
    assert back[0].rel_path == figure.rel_path
    assert (back[0].width, back[0].height, back[0].page) == (237, 496, 10)


def test_one_diagram_shared_by_two_chunks_is_stored_once(store, doc):
    rel = figure_rel_path(doc.doc_id, "shared.png")
    a = _chunk_with(doc, [Figure(doc.doc_id, 10, rel, 100, 100)], text="First passage.")
    b = _chunk_with(doc, [Figure(doc.doc_id, 11, rel, 100, 100)], text="Second passage.")
    store.add_chunks([a, b])
    store.add_chunk_figures([a, b])

    assert store.count_figures() == 1
    assert store.get_figures(a.chunk_id)[0].figure_id == store.get_figures(b.chunk_id)[0].figure_id


def test_a_chunk_with_no_figures_returns_none(store, doc):
    chunk = _chunk_with(doc, [])
    store.add_chunks([chunk])
    store.add_chunk_figures([chunk])
    assert store.get_figures(chunk.chunk_id) == []


def test_a_figure_does_not_spread_to_a_sibling_in_the_same_section(store, doc):
    """Decided 2026-08-31: a figure stays on the chunk it physically sits in.

    Samsung puts the illustration under a section intro while "how do I…"
    answers cite the procedure subsection below it, so figures miss more often
    than they fire. That is the accepted cost. A figure shown beside a procedure
    it does not depict is a claim the manual never made, and it would carry the
    same authority as the cited text.

    If this test is failing because someone widened the mapping to siblings, the
    parent section, or the page range, that is the change to reconsider — not
    this assertion. See CLAUDE.md, Architecture invariants.
    """
    figure = Figure(doc.doc_id, 10, figure_rel_path(doc.doc_id, "intro.png"), 1, 1)
    intro = _chunk_with(doc, [figure], text="Multi window lets you run two apps.")
    procedure = _chunk_with(doc, [], text="Tap Recents, then Open in split screen view.")
    # Same section, same page, adjacent ids — every reason to bleed across.
    assert intro.section_path == procedure.section_path
    store.add_chunks([intro, procedure])
    store.add_chunk_figures([intro, procedure])

    assert len(store.get_figures(intro.chunk_id)) == 1
    assert store.get_figures(procedure.chunk_id) == []


def test_figure_path_resolves_under_the_store_root(store, doc):
    figure = Figure(doc.doc_id, 10, figure_rel_path(doc.doc_id, "a.png"), 1, 1)
    assert store.figure_path(figure) == store.root / figure.rel_path


def test_deleting_a_document_takes_its_figures(store, doc):
    """The store is rebuilt wholesale, but a dangling figure row would outlive
    the chunk it illustrates and resolve to a file that is no longer there."""
    figure = Figure(doc.doc_id, 10, figure_rel_path(doc.doc_id, "a.png"), 1, 1)
    chunk = _chunk_with(doc, [figure])
    store.add_chunks([chunk])
    store.add_chunk_figures([chunk])

    store.conn.execute("DELETE FROM documents WHERE doc_id=?", (doc.doc_id,))
    store.conn.commit()
    assert store.count_figures() == 0


# --- what reaches the answer ----------------------------------------------


def _citation(marker, figures) -> Citation:
    return Citation(
        marker=marker, chunk_id=marker, model="Galaxy A05", page_start=10,
        page_end=10, section_path="Camera", snippet="…", figures=figures,
    )


def test_answer_figures_are_ordered_by_first_citation():
    one = Figure("d", 10, "figures/d/one.png", 1, 1)
    two = Figure("d", 11, "figures/d/two.png", 1, 1)
    answer = Answer(question="q", text="a [1][2]",
                    citations=[_citation(1, [one]), _citation(2, [two])])
    assert [f.rel_path for f, _ in answer.figures()] == [one.rel_path, two.rel_path]
    assert [marker for _, marker in answer.figures()] == [1, 2]


def test_the_same_diagram_cited_twice_renders_once():
    same = Figure("d", 10, "figures/d/one.png", 1, 1)
    answer = Answer(question="q", text="a [1][2]",
                    citations=[_citation(1, [same]), _citation(2, [same])])
    assert len(answer.figures()) == 1


def test_a_refusal_shows_no_figures():
    """There is no claim for a picture to illustrate."""
    figure = Figure("d", 10, "figures/d/one.png", 1, 1)
    answer = Answer(question="q", text="not covered", refused=True,
                    citations=[_citation(1, [figure])])
    assert answer.figures() == []


def test_a_text_only_answer_shows_no_figures():
    answer = Answer(question="q", text="a [1]", citations=[_citation(1, [])])
    assert answer.figures() == []
