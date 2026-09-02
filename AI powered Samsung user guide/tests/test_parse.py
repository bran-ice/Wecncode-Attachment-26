"""Parser tests.

Built on synthetic PDFs so they are fast and deterministic; the shapes mirror
what the real manuals do (running header, page-number footer, outline-driven
headings, bold lead-ins, numbered steps, diagram callouts).
"""

import pytest

from ingest.parse import Block, _looks_like_prose, parse_pdf


@pytest.fixture
def manual(tmp_path):
    """A miniature manual with the layout traits that broke the first parser."""
    import pymupdf

    doc = pymupdf.open()
    body, heading, big = 13.6, 19.5, 25.3

    # `insert_text` places the *baseline*, so a heading's top edge sits roughly
    # `fontsize` above y. Real manuals put the running header's top edge at ~2%
    # of page height and the first heading's at ~8%; these coordinates match.
    def page(lines):
        p = doc.new_page(width=595, height=842)
        p.insert_text((45, 30), "Getting started", fontsize=body)  # running header
        for y, text, size, font in lines:
            p.insert_text((45, y), text, fontsize=size, fontname=font)
        p.insert_text((291, 815), str(doc.page_count), fontsize=body)  # page number
        return p

    page([(100, "Introduction", big, "hebo"),
          (140, "Get to know the basics of your device.", body, "helv")])
    page([(100, "Charging the battery", heading, "hebo"),
          (140, "Connect the USB cable to the USB power adapter.", body, "helv"),
          (170, "1 Open Settings, tap Battery, and then tap Charging.", body, "hebo"),
          (200, "2 Place the other device on the centre of your phone.", body, "hebo"),
          (240, "Battery.", body, "hebo"),
          (270, "Use only Samsung-approved chargers, model EP-TA845.", body, "helv")])
    page([(100, "Wireless power sharing", heading, "hebo"),
          (140, "You can charge another device with your phone's battery.", body, "helv"),
          (430, "1", big, "hebo"),
          (470, "2", big, "hebo")])

    doc.set_toc([
        [1, "Getting started", 1],
        [2, "Introduction", 1],
        [2, "Charging the battery", 2],
        [3, "Wireless power sharing", 3],
    ])
    path = tmp_path / "TEST_UM_EN.pdf"
    doc.save(path)
    doc.close()
    return path


def texts(parsed, kind=None):
    return [b.text for b in parsed.blocks if kind is None or b.kind == kind]


def test_outline_drives_section_paths(manual):
    parsed = parse_pdf(manual)
    paths = {b.section_path for b in parsed.blocks}
    assert "Getting started > Introduction" in paths
    assert "Getting started > Charging the battery" in paths
    assert "Getting started > Charging the battery > Wireless power sharing" in paths


def test_heading_levels_come_from_the_outline(manual):
    parsed = parse_pdf(manual)
    levels = {b.text: b.level for b in parsed.blocks if b.is_heading()}
    assert levels["Charging the battery"] == 2
    assert levels["Wireless power sharing"] == 3


def test_chapter_only_in_the_outline_still_appears_in_paths(manual):
    """"Getting started" is drawn only as a running header, which is stripped.
    Its ancestry has to come from the outline or every section loses its
    chapter."""
    parsed = parse_pdf(manual)
    assert all(
        b.section_path.startswith("Getting started")
        for b in parsed.blocks
        if b.section_path
    )


def test_running_header_and_page_number_stripped(manual):
    """Chrome repeated on every page would otherwise appear in every chunk."""
    parsed = parse_pdf(manual)
    body = " ".join(texts(parsed, "body"))
    assert "Getting started" not in body
    assert not any(t.strip().isdigit() for t in texts(parsed))


def test_numbered_steps_are_body_not_headings(manual):
    """Steps are set in bold here; typography alone would file each as a heading
    and every procedure would fragment into one-step sections."""
    parsed = parse_pdf(manual)
    headings = texts(parsed, "heading")
    assert not any(h.startswith(("1 ", "2 ")) for h in headings)
    body = " ".join(texts(parsed, "body"))
    assert "Open Settings" in body and "Place the other device" in body


def test_bold_lead_in_ending_in_period_is_not_a_heading(manual):
    parsed = parse_pdf(manual)
    assert "Battery." not in texts(parsed, "heading")


def test_diagram_callout_numbers_are_dropped(manual):
    """Figure labels are large and bold — indistinguishable from headings by
    typography, but they are never words."""
    parsed = parse_pdf(manual)
    assert "1" not in texts(parsed, "heading")
    assert "2" not in texts(parsed, "heading")


def test_part_numbers_survive_parsing(manual):
    """The whole reason BM25 is in this system."""
    parsed = parse_pdf(manual)
    assert "EP-TA845" in " ".join(texts(parsed, "body"))


def test_pages_are_one_based_and_accurate(manual):
    parsed = parse_pdf(manual)
    charging = [b for b in parsed.blocks if "USB power adapter" in b.text]
    assert charging and charging[0].page == 2


def test_body_size_detected(manual):
    assert parse_pdf(manual).body_size == pytest.approx(13.6, abs=0.2)


def test_max_pages_limits_work(manual):
    assert max(b.page for b in parse_pdf(manual, max_pages=2).blocks) <= 2


@pytest.mark.parametrize(
    "text,is_prose",
    [
        ("1 Open Settings and tap Battery.", True),
        ("• Use only approved chargers", True),
        ("Battery.", True),
        ("Note that this may vary", True),
        ("Wireless power sharing", False),
        ("Charging the battery", False),
    ],
)
def test_prose_detection(text, is_prose):
    assert _looks_like_prose(text) is is_prose


def test_block_is_heading():
    assert Block("x", 1, "heading").is_heading()
    assert not Block("x", 1, "body").is_heading()
