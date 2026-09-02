from core.schema import Chunk, Citation


def test_embed_text_prefixes_section_path():
    c = Chunk(
        doc_id="d",
        text="Tap Always On Display.",
        section_path="Settings > Lock screen",
        page_start=1,
        page_end=1,
    )
    assert c.embed_text().startswith("Settings > Lock screen")
    assert "Tap Always On Display." in c.embed_text()


def test_embed_text_without_section_path_is_just_text():
    c = Chunk(doc_id="d", text="Body only.", page_start=1, page_end=1)
    assert c.embed_text() == "Body only."


def test_citation_label_single_and_range():
    base = dict(chunk_id=1, model="Galaxy S24", section_path="", snippet="")
    assert Citation(marker=1, page_start=5, page_end=5, **base).label() == "Galaxy S24 p.5"
    assert (
        Citation(marker=1, page_start=5, page_end=7, **base).label()
        == "Galaxy S24 pp.5-7"
    )
