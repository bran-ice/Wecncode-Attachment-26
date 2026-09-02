import json

import pytest

from ingest.acquire import (
    AcquisitionError,
    Fetcher,
    acquire,
    build_record,
    filename_for,
    load_manifest,
    read_url_list,
    save_manifest,
    sha256_file,
)


# --------------------------------------------------------------- fake network


class FakeResponse:
    def __init__(self, body: bytes, content_type="application/pdf", status=200):
        self._body = body
        self.headers = {"content-type": content_type}
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AcquisitionError(f"HTTP {self.status_code}")

    def iter_content(self, n):
        yield self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeSession:
    def __init__(self, responses: dict):
        self.responses = responses
        self.headers = {}
        self.calls: list[str] = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        if url not in self.responses:
            raise AcquisitionError(f"unexpected URL {url}")
        return self.responses[url]


class AllowAllRobots:
    def allowed(self, url):
        return True

    def crawl_delay(self, url, default=1.0):
        return default


class DenyAllRobots:
    def allowed(self, url):
        return False

    def crawl_delay(self, url, default=1.0):
        return default


@pytest.fixture
def pdf_bytes():
    """A real one-page PDF, so page counting and metadata parsing are exercised."""
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Galaxy S24 Ultra User Manual SM-S928U")
    doc.set_metadata({"title": "Galaxy S24 Ultra User Manual"})
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def clock():
    """Controllable time, so rate-limit tests are instant and deterministic."""

    class Clock:
        def __init__(self):
            self.now = 0.0
            self.slept: list[float] = []

        def sleep(self, seconds):
            self.slept.append(seconds)
            self.now += seconds

        def monotonic(self):
            return self.now

    return Clock()


def make_fetcher(tmp_path, responses, clock, robots=None, **kw):
    return Fetcher(
        tmp_path / "raw",
        session=FakeSession(responses),
        robots=robots or AllowAllRobots(),
        sleep=clock.sleep,
        clock=clock.monotonic,
        **kw,
    )


# ------------------------------------------------------------------- fetching


def test_downloads_pdf(tmp_path, pdf_bytes, clock):
    url = "https://example.com/SM-S928U_UM_EN.pdf"
    fetcher = make_fetcher(tmp_path, {url: FakeResponse(pdf_bytes)}, clock)
    path = fetcher.fetch(url)
    assert path.read_bytes() == pdf_bytes
    assert path.name == "SM-S928U_UM_EN.pdf"


def test_second_run_downloads_nothing(tmp_path, pdf_bytes, clock):
    url = "https://example.com/m.pdf"
    fetcher = make_fetcher(tmp_path, {url: FakeResponse(pdf_bytes)}, clock)
    fetcher.fetch(url)
    fetcher.fetch(url)
    assert len(fetcher.session.calls) == 1


def test_rate_limit_respected(tmp_path, pdf_bytes, clock):
    urls = [f"https://example.com/m{i}.pdf" for i in range(3)]
    fetcher = make_fetcher(
        tmp_path, {u: FakeResponse(pdf_bytes) for u in urls}, clock, min_delay=1.0
    )
    for u in urls:
        fetcher.fetch(u)
    assert clock.slept == [1.0, 1.0]  # no sleep before the first request


def test_html_error_page_is_not_saved_as_a_manual(tmp_path, clock):
    """Expired links return an HTML 404 body; silently indexing it would poison
    the corpus with a page of navigation chrome."""
    url = "https://example.com/gone.pdf"
    fetcher = make_fetcher(
        tmp_path, {url: FakeResponse(b"<html>404</html>", "text/html")}, clock
    )
    with pytest.raises(AcquisitionError, match="not a PDF"):
        fetcher.fetch(url)
    assert not (tmp_path / "raw" / "gone.pdf").exists()


def test_drm_wrapped_file_is_rejected(tmp_path, clock):
    """Samsung's NASCA DRM containers arrive as `application/pdf` with a
    plausible size; only the magic bytes give them away."""
    url = "https://example.com/drm.pdf"
    body = b"<## NASCA DRM FILE - v1.0 ##>" + b"\x00" * 1000
    fetcher = make_fetcher(tmp_path, {url: FakeResponse(body)}, clock)
    with pytest.raises(AcquisitionError, match="DRM-protected"):
        fetcher.fetch(url)
    assert not (tmp_path / "raw" / "drm.pdf").exists()


def test_non_pdf_bytes_rejected_even_with_pdf_content_type(tmp_path, clock):
    url = "https://example.com/x.pdf"
    fetcher = make_fetcher(tmp_path, {url: FakeResponse(b"\x89PNG\r\n\x1a\n" * 20)}, clock)
    with pytest.raises(AcquisitionError, match="did not return a PDF"):
        fetcher.fetch(url)


def test_valid_pdf_passes_the_magic_check(tmp_path, pdf_bytes, clock):
    url = "https://example.com/ok.pdf"
    fetcher = make_fetcher(tmp_path, {url: FakeResponse(pdf_bytes)}, clock)
    assert fetcher.fetch(url) is not None


def test_failed_download_leaves_no_partial_file(tmp_path, clock):
    url = "https://example.com/boom.pdf"
    fetcher = make_fetcher(tmp_path, {url: FakeResponse(b"x", "text/html")}, clock)
    with pytest.raises(AcquisitionError):
        fetcher.fetch(url)
    assert list((tmp_path / "raw").glob("*")) == []


def test_robots_disallowed_url_skipped_by_default(tmp_path, pdf_bytes, clock):
    url = "https://downloadcenter.samsung.com/m.pdf"
    fetcher = make_fetcher(
        tmp_path, {url: FakeResponse(pdf_bytes)}, clock, robots=DenyAllRobots()
    )
    assert fetcher.fetch(url) is None


def test_user_directed_flag_allows_disallowed_url(tmp_path, pdf_bytes, clock):
    url = "https://downloadcenter.samsung.com/m.pdf"
    fetcher = make_fetcher(
        tmp_path,
        {url: FakeResponse(pdf_bytes)},
        clock,
        robots=DenyAllRobots(),
        user_directed=True,
    )
    assert fetcher.fetch(url) is not None


def test_filename_for_handles_query_strings():
    assert filename_for("https://x.com/a/UM_EN.pdf?ver=2") == "UM_EN.pdf"
    assert filename_for("https://x.com/download").endswith(".pdf")


def test_filename_comes_from_query_when_path_is_a_shared_endpoint():
    """Every Samsung manual URL has the same path, `ContentsFile.aspx`. Naming
    by path collapses the whole corpus onto one file, and the skip-if-present
    check then discards every manual after the first."""
    url = (
        "https://org.downloadcenter.samsung.com/downloadfile/ContentsFile.aspx"
        "?CDSite=UNI_CA&ModelName=SM-S928W&CttFileID=11048160&CDCttType=UM"
        "&VPath=UM%2F202511%2F20251103185247817%2FS93X_S92X_UG_CA_16_ENG_D3.pdf"
    )
    assert filename_for(url) == "S93X_S92X_UG_CA_16_ENG_D3.pdf"


def test_distinct_manuals_get_distinct_filenames():
    base = (
        "https://org.downloadcenter.samsung.com/downloadfile/ContentsFile.aspx"
        "?CDCttType=UM&VPath=UM%2F202511%2Fx%2F"
    )
    names = {filename_for(base + n) for n in ("S91X_ENG.pdf", "S93X_ENG.pdf")}
    assert names == {"S91X_ENG.pdf", "S93X_ENG.pdf"}


# ------------------------------------------------------------------- manifest


def _write_pdf(tmp_path, name, pdf_bytes):
    raw = tmp_path / "raw"
    raw.mkdir(exist_ok=True)
    (raw / name).write_bytes(pdf_bytes)
    return raw / name


def test_build_record_reads_pages_and_metadata(tmp_path, pdf_bytes):
    path = _write_pdf(tmp_path, "SM-S928U_UM_EN_OS14.pdf", pdf_bytes)
    record = build_record(path, url="https://example.com/x.pdf")
    assert record.model == "Galaxy S24 Ultra"
    assert record.language == "en"
    assert record.os_version == "Android 14"
    assert record.n_pages == 1
    assert record.sha256 == sha256_file(path)
    assert record.doc_id == record.sha256


def test_manifest_roundtrip_and_schema(tmp_path, pdf_bytes):
    path = _write_pdf(tmp_path, "SM-S928U_UM_EN.pdf", pdf_bytes)
    save_manifest(tmp_path / "store", [build_record(path)])

    payload = json.loads((tmp_path / "store" / "manifest.json").read_text())
    assert payload["version"] == 1 and "updated_at" in payload
    entry = payload["manuals"][0]
    for field in ("filename", "sha256", "n_pages", "model", "language", "acquired_at"):
        assert field in entry

    assert list(load_manifest(tmp_path / "store"))[0] == entry["sha256"]


def test_scan_indexes_local_pdfs(tmp_path, pdf_bytes):
    _write_pdf(tmp_path, "SM-S928U_UM_EN.pdf", pdf_bytes)
    # A trailing comment after %%EOF changes the hash while staying a valid PDF.
    _write_pdf(tmp_path, "SM-S921B_UM_EN.pdf", pdf_bytes + b"\n% variant\n")
    records = acquire(tmp_path / "raw", tmp_path / "store")
    assert {r.model for r in records} == {"Galaxy S24 Ultra", "Galaxy S24"}


def test_language_filter_excludes_non_english(tmp_path, pdf_bytes):
    _write_pdf(tmp_path, "SM-S928U_UM_KO.pdf", pdf_bytes)
    assert acquire(tmp_path / "raw", tmp_path / "store") == []
    assert len(acquire(tmp_path / "raw", tmp_path / "store", english_only=False)) == 1


def test_dedup_by_content_hash(tmp_path, pdf_bytes):
    """The same manual downloaded under two names must be indexed once."""
    _write_pdf(tmp_path, "SM-S928U_UM_EN.pdf", pdf_bytes)
    _write_pdf(tmp_path, "SM-S928U_UM_EN(1).pdf", pdf_bytes)
    assert len(acquire(tmp_path / "raw", tmp_path / "store")) == 1


def test_rerun_is_idempotent(tmp_path, pdf_bytes):
    _write_pdf(tmp_path, "SM-S928U_UM_EN.pdf", pdf_bytes)
    first = acquire(tmp_path / "raw", tmp_path / "store")
    second = acquire(tmp_path / "raw", tmp_path / "store")
    assert [r.sha256 for r in first] == [r.sha256 for r in second]


def test_unreadable_pdf_is_skipped_not_fatal(tmp_path, pdf_bytes):
    _write_pdf(tmp_path, "SM-S928U_UM_EN.pdf", pdf_bytes)
    _write_pdf(tmp_path, "broken_EN.pdf", b"not a pdf at all")
    records = acquire(tmp_path / "raw", tmp_path / "store")
    assert [r.filename for r in records] == ["SM-S928U_UM_EN.pdf"]


def test_missing_url_list_gives_actionable_error(tmp_path):
    with pytest.raises(AcquisitionError, match="--scan"):
        read_url_list(tmp_path / "nope.txt")


def test_url_list_ignores_comments_and_blanks(tmp_path):
    path = tmp_path / "sources.txt"
    path.write_text(
        "# Galaxy S24 Ultra\nhttps://x.com/a.pdf\n\n  \nhttps://x.com/b.pdf  # note\n",
        encoding="utf-8",
    )
    assert read_url_list(path) == ["https://x.com/a.pdf", "https://x.com/b.pdf"]
