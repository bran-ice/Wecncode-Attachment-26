import pytest

from ingest.discover import (
    Discoverer,
    ManualLink,
    base_code,
    discover,
    newest_per_model,
    write_sources,
)

SITEMAP = """<?xml version="1.0"?>
<urlset>
  <url><loc>https://www.samsung.com/ca/support/model/SM-S928WZTFXAC/</loc></url>
  <url><loc>https://www.samsung.com/ca/support/model/SM-S928WZKAXAC/</loc></url>
  <url><loc>https://www.samsung.com/ca/support/model/SM-S911WZAEXAC/</loc></url>
  <url><loc>https://www.samsung.com/ca/support/model/SM-F956WZKAXAC/</loc></url>
  <url><loc>https://www.samsung.com/ca/support/model/SM-A546WZKBXAC/</loc></url>
  <url><loc>https://www.samsung.com/ca/support/model/SM-T870NZKAXAC/</loc></url>
  <url><loc>https://www.samsung.com/ca/support/home-appliances/</loc></url>
</urlset>"""


def model_page(*entries: str) -> str:
    links = "".join(
        f'<a href="/downloadfile/ContentsFile.aspx?CDSite=UNI_CA&amp;ModelName=SM-S928W'
        f"&amp;CttFileID={i}&amp;CDCttType=UM&amp;VPath=UM%2F{e[0]}%2F{e[0]}01120000%2F{e[1]}\">PDF</a>"
        for i, e in enumerate(entries)
    )
    return f"<html><body>{links}</body></html>"


class FakeSession:
    def __init__(self, pages: dict):
        self.pages = pages
        self.headers = {}
        self.calls: list[str] = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        body = self.pages.get(url)
        if body is None:
            raise AssertionError(f"unexpected fetch: {url}")

        class R:
            text = body

            def raise_for_status(self):
                pass

        return R()


class AllowAllRobots:
    def allowed(self, url):
        return True

    def crawl_delay(self, url, default=1.0):
        return default


class DenyDownloadHost:
    """Mirrors reality: support pages allowed, the PDF host is not."""

    def allowed(self, url):
        return "downloadcenter" not in url

    def crawl_delay(self, url, default=1.0):
        return default


@pytest.fixture
def clock():
    class Clock:
        def __init__(self):
            self.now = 0.0
            self.slept = []

        def sleep(self, s):
            self.slept.append(s)
            self.now += s

        def monotonic(self):
            return self.now

    return Clock()


def make(pages, clock, robots=None):
    return Discoverer(
        region="ca",
        session=FakeSession(pages),
        robots=robots or AllowAllRobots(),
        sleep=clock.sleep,
        clock=clock.monotonic,
    )


# ------------------------------------------------------------------- sitemap


def test_base_code_strips_colour_and_carrier_suffix():
    assert base_code("SM-S928WZTFXAC") == "SM-S928W"
    assert base_code("SM-F956BZK8XAC") == "SM-F956B"
    assert base_code("weird") == "WEIRD"


def test_list_skus_filters_to_requested_series_and_dedupes(clock):
    d = make({"https://www.samsung.com/ca/support/sitemap.xml": SITEMAP}, clock)
    skus = d.list_skus(["S"])
    # Two S928 SKUs collapse to one model; S911 kept; tablet/fold/A excluded.
    assert [base_code(s) for s in skus] == ["SM-S911W", "SM-S928W"]


def test_list_skus_multiple_series(clock):
    d = make({"https://www.samsung.com/ca/support/sitemap.xml": SITEMAP}, clock)
    assert [base_code(s) for s in d.list_skus(["S", "FOLD", "A"])] == [
        "SM-A546W",
        "SM-F956W",
        "SM-S911W",
        "SM-S928W",
    ]


def test_tablets_are_not_phones(clock):
    d = make({"https://www.samsung.com/ca/support/sitemap.xml": SITEMAP}, clock)
    assert not any("T870" in s for s in d.list_skus(["S", "FOLD", "FLIP", "A"]))


# --------------------------------------------------------------- model pages


def test_manual_links_extracted_and_decoded(clock):
    url = "https://www.samsung.com/ca/support/model/SM-S928WZTFXAC/"
    d = make({url: model_page(("202511", "S93X_S92X_UG_CA_16_ENG_D3.pdf"))}, clock)
    links = d.manual_links("SM-S928WZTFXAC")
    assert len(links) == 1
    assert links[0].filename == "S93X_S92X_UG_CA_16_ENG_D3.pdf"
    assert links[0].yyyymm == "202511"
    assert links[0].base_code == "SM-S928W"
    assert "&amp;" not in links[0].url  # HTML entities decoded, or the URL 404s


def test_non_english_manuals_excluded(clock):
    url = "https://www.samsung.com/ca/support/model/SM-S928WZTFXAC/"
    d = make(
        {
            url: model_page(
                ("202511", "S93X_UG_CA_16_ENG_D3.pdf"),
                ("202511", "S93X_UG_CA_16_FR_D3.pdf"),
            )
        },
        clock,
    )
    assert [l.filename for l in d.manual_links("SM-S928WZTFXAC")] == [
        "S93X_UG_CA_16_ENG_D3.pdf"
    ]


def test_safety_leaflets_excluded(clock):
    """Not user manuals; indexing them dilutes retrieval with legal boilerplate."""
    url = "https://www.samsung.com/ca/support/model/SM-S928WZTFXAC/"
    d = make(
        {
            url: model_page(
                ("202401", "Safety_information_Rev.1.9.5_EN_230407.pdf"),
                ("202502", "S92X_UG_CA_15_Eng_D04.pdf"),
            )
        },
        clock,
    )
    assert [l.filename for l in d.manual_links("SM-S928WZTFXAC")] == [
        "S92X_UG_CA_15_Eng_D04.pdf"
    ]


def test_rate_limited_between_pages(clock):
    pages = {
        "https://www.samsung.com/ca/support/sitemap.xml": SITEMAP,
        "https://www.samsung.com/ca/support/model/SM-S911WZAEXAC/": model_page(
            ("202506", "S91X_UG_CA_15_ENG_D3.pdf")
        ),
        "https://www.samsung.com/ca/support/model/SM-S928WZTFXAC/": model_page(
            ("202511", "S93X_S92X_UG_CA_16_ENG_D3.pdf")
        ),
    }
    d = make(pages, clock)
    discover(["S"], discoverer=d)
    assert clock.slept == [1.0, 1.0]  # sitemap, then one delay before each page


def test_download_host_is_never_fetched(clock):
    """The PDF host disallows robots — discovery must only ever write its URL."""
    pages = {
        "https://www.samsung.com/ca/support/sitemap.xml": SITEMAP,
        "https://www.samsung.com/ca/support/model/SM-S911WZAEXAC/": model_page(
            ("202506", "S91X_UG_CA_15_ENG_D3.pdf")
        ),
        "https://www.samsung.com/ca/support/model/SM-S928WZTFXAC/": model_page(
            ("202511", "S93X_UG_CA_16_ENG_D3.pdf")
        ),
    }
    d = make(pages, clock, robots=DenyDownloadHost())
    links = discover(["S"], discoverer=d)
    assert links and all("downloadcenter" in l.url for l in links)
    assert not any("downloadcenter" in call for call in d.session.calls)


def test_a_failing_model_page_does_not_abort_the_run(clock):
    pages = {
        "https://www.samsung.com/ca/support/sitemap.xml": SITEMAP,
        "https://www.samsung.com/ca/support/model/SM-S928WZTFXAC/": model_page(
            ("202511", "S93X_UG_CA_16_ENG_D3.pdf")
        ),
        # SM-S911WZAEXAC deliberately absent -> raises
    }
    d = make(pages, clock)
    assert [l.base_code for l in discover(["S"], discoverer=d)] == ["SM-S928W"]


# ----------------------------------------------------------------- selection


def test_newest_per_model_wins():
    """One manual per phone: reissues for each OS upgrade would contradict
    each other in the corpus."""
    links = [
        ManualLink("SKU", "SM-S928W", "u1", "old_ENG.pdf", "202402"),
        ManualLink("SKU", "SM-S928W", "u2", "new_ENG.pdf", "202511"),
        ManualLink("SKU", "SM-S911W", "u3", "s23_ENG.pdf", "202506"),
    ]
    kept = newest_per_model(links)
    assert [l.filename for l in kept] == ["s23_ENG.pdf", "new_ENG.pdf"]


def test_shared_manual_downloaded_once_but_records_every_model():
    """Samsung ships one manual per family generation: the S24 and S25 lines
    share a file. Eight models must not mean eight downloads of the same 15 MB."""
    from ingest.discover import dedupe_by_file

    shared = "S93X_S92X_UG_CA_16_ENG_D3.pdf"
    links = [
        ManualLink("SKU1", "SM-S921W", "https://x/shared.pdf", shared, "202511"),
        ManualLink("SKU2", "SM-S928W", "https://x/shared.pdf", shared, "202511"),
        ManualLink("SKU3", "SM-S938W", "https://x/shared.pdf", shared, "202511"),
        ManualLink("SKU4", "SM-S911W", "https://x/s23.pdf", "S91X_ENG.pdf", "202511"),
    ]
    kept = dedupe_by_file(links)
    assert len(kept) == 2
    by_file = {l.filename: l for l in kept}
    assert by_file[shared].models() == ["SM-S921W", "SM-S928W", "SM-S938W"]
    assert by_file["S91X_ENG.pdf"].models() == ["SM-S911W"]


def test_write_sources_is_readable_by_the_acquirer(tmp_path):
    from ingest.acquire import read_url_list

    links = [ManualLink("SKU", "SM-S928W", "https://x/a.pdf", "a_ENG.pdf", "202511")]
    path = write_sources(links, tmp_path / "sources.txt")
    assert read_url_list(path) == ["https://x/a.pdf"]
