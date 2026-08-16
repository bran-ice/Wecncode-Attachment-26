"""Acquire manual PDFs into `data/raw/` and record a manifest.

Not a crawler. Samsung's manual host disallows all robots (see `ingest/robots.py`),
so acquisition works from an explicit list of URLs the user collected themselves,
or from PDFs dropped straight into `data/raw/`. Everything downstream is
indifferent to which route a file took.

    python -m ingest.acquire --urls sources.txt
    python -m ingest.acquire --scan            # adopt PDFs already in data/raw
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import parse_qsl, unquote, urlparse

import requests

from core.config import load_settings
from core.logging_setup import get_logger, setup_logging
from ingest import metadata as meta_mod
from ingest.robots import USER_AGENT, RobotsCache

log = get_logger(__name__)

MANIFEST_NAME = "manifest.json"
CHUNK_BYTES = 1 << 16


@dataclass
class ManualRecord:
    """One acquired file, as recorded in the manifest."""

    filename: str
    url: str
    sha256: str
    bytes: int
    n_pages: int
    model: str
    model_codes: list[str]
    language: str
    region: Optional[str]
    os_version: Optional[str]
    title: str
    acquired_at: str

    @property
    def doc_id(self) -> str:
        return self.sha256


class AcquisitionError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(CHUNK_BYTES):
            digest.update(block)
    return digest.hexdigest()


def read_url_list(path: Path) -> list[str]:
    """One URL per line; `#` comments and blank lines ignored."""
    if not path.exists():
        raise AcquisitionError(
            f"No URL list at {path}. Create one with a manual URL per line, or use "
            "--scan to adopt PDFs you have already placed in data/raw/."
        )
    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            urls.append(line)
    return urls


def filename_for(url: str) -> str:
    """Pick a local filename for a manual URL.

    Samsung's download URLs all share one path — `.../ContentsFile.aspx` — and
    carry the real filename in a query parameter (`VPath=UM/202511/.../S93X....pdf`).
    Naming files after the path would collapse every manual onto one name, and
    the "already have it" check would then skip the entire corpus after the
    first file. So query values win when one of them looks like a PDF.
    """
    parsed = urlparse(url)
    for _key, value in parse_qsl(parsed.query):
        candidate = unquote(value).replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
        if candidate.lower().endswith(".pdf"):
            return candidate

    name = parsed.path.rstrip("/").rsplit("/", 1)[-1]
    if not name.lower().endswith(".pdf"):
        name = f"{name or 'manual'}.pdf"
    return name


class Fetcher:
    """Rate-limited, resumable downloader for a user-supplied URL list."""

    def __init__(
        self,
        raw_dir: Path,
        min_delay: float = 1.0,
        user_directed: bool = False,
        session: Optional[requests.Session] = None,
        robots: Optional[RobotsCache] = None,
        sleep=time.sleep,
        clock=time.monotonic,
    ):
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.min_delay = min_delay
        self.user_directed = user_directed
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.robots = robots or RobotsCache()
        self._sleep = sleep
        self._clock = clock
        self._last_request: Optional[float] = None

    def _throttle(self, url: str) -> None:
        delay = max(self.min_delay, self.robots.crawl_delay(url, self.min_delay))
        if self._last_request is not None:
            elapsed = self._clock() - self._last_request
            if elapsed < delay:
                self._sleep(delay - elapsed)
        self._last_request = self._clock()

    def fetch(self, url: str) -> Optional[Path]:
        """Download one URL. Returns the local path, or None if skipped."""
        if not self.robots.allowed(url):
            if not self.user_directed:
                log.warning(
                    "robots.txt disallows %s — skipping. Pass --user-directed if you "
                    "collected this URL yourself and are downloading it as a user.",
                    url,
                )
                return None
            log.info("robots.txt disallows %s; proceeding as a user-directed download", url)

        dest = self.raw_dir / filename_for(url)
        if dest.exists():
            log.info("Already have %s — skipping download", dest.name)
            return dest

        self._throttle(url)
        log.info("Fetching %s", url)
        tmp = dest.with_suffix(dest.suffix + ".part")
        try:
            with self.session.get(url, stream=True, timeout=60) as response:
                response.raise_for_status()
                ctype = response.headers.get("content-type", "")
                if "pdf" not in ctype.lower() and "octet-stream" not in ctype.lower():
                    raise AcquisitionError(
                        f"{url} returned {ctype or 'no content-type'}, not a PDF. "
                        "The link may have expired or require a browser session."
                    )
                with tmp.open("wb") as fh:
                    for block in response.iter_content(CHUNK_BYTES):
                        fh.write(block)
            _reject_if_not_a_pdf(tmp, url)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
        tmp.replace(dest)  # never leave a partial file looking like a manual
        log.info("Saved %s (%.1f MB)", dest.name, dest.stat().st_size / 1e6)
        return dest


def _reject_if_not_a_pdf(path: Path, url: str) -> None:
    """Verify the bytes, not the Content-Type header.

    Samsung serves some manuals wrapped in its NASCA document DRM. Those come
    back as `application/pdf` with a plausible size, so only the magic number
    tells them apart — and a DRM container that reaches `data/raw/` fails much
    later, during parsing, where the cause is far from obvious.
    """
    with path.open("rb") as fh:
        head = fh.read(16)

    if head.startswith(b"%PDF"):
        return

    if b"NASCA" in head or head.startswith(b"<##"):
        raise AcquisitionError(
            f"{url} is DRM-protected (Samsung NASCA), not a readable PDF. "
            "Look for the same manual on another regional Samsung site."
        )
    raise AcquisitionError(f"{url} did not return a PDF (starts with {head[:8]!r}).")


def describe_pdf(path: Path) -> tuple[int, dict, str]:
    """Return (page count, PDF metadata, first-page text)."""
    import pymupdf

    with pymupdf.open(path) as doc:
        first = doc[0].get_text() if doc.page_count else ""
        return doc.page_count, dict(doc.metadata or {}), first


def load_coverage(catalog_dir: Path) -> dict[str, dict]:
    """filename -> {model_codes, yyyymm}, written by `ingest.discover`."""
    path = Path(catalog_dir) / "coverage.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_record(path: Path, url: str = "", coverage: dict | None = None) -> ManualRecord:
    meta = meta_mod.from_filename(path)
    n_pages, pdf_meta, first_page = describe_pdf(path)
    meta = meta_mod.enrich_from_pdf(meta, pdf_meta, first_page)

    # Discovery observed which SKU pages linked to this file, so it beats any
    # inference from a wildcard filename like `S91X_S90X_UG_CA_16_ENG_D2.pdf`.
    entry = (coverage or {}).get(path.name)
    if entry and entry.get("model_codes"):
        # Union the two sources: discovery sees models whose filenames hide them
        # behind wildcards (`S91X_S90X`), while filenames like
        # `SM-F946W_F936W_F926W` name models whose support pages happened to link
        # a newer manual. Each covers the other's blind spot.
        codes = list(entry["model_codes"])
        # Filename codes are bare ("S921"); discovery's are full SKUs
        # ("SM-S921W"). Only add what the SKU list doesn't already name.
        codes += [c for c in meta.model_codes if not any(c in known for known in codes)]
        meta.model_codes = codes
        meta.model = meta_mod.display_model(codes) or meta.model

    return ManualRecord(
        filename=path.name,
        url=url,
        sha256=sha256_file(path),
        bytes=path.stat().st_size,
        n_pages=n_pages,
        model=meta.model or "unknown",
        model_codes=meta.model_codes,
        language=meta.language,
        region=meta.region,
        os_version=meta.os_version,
        title=meta.title or path.stem,
        acquired_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def load_manifest(catalog_dir: Path) -> dict[str, ManualRecord]:
    path = Path(catalog_dir) / MANIFEST_NAME
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {r["sha256"]: ManualRecord(**r) for r in raw.get("manuals", [])}


def save_manifest(catalog_dir: Path, records: Iterable[ManualRecord]) -> Path:
    catalog_dir = Path(catalog_dir)
    catalog_dir.mkdir(parents=True, exist_ok=True)
    path = catalog_dir / MANIFEST_NAME
    payload = {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "manuals": [asdict(r) for r in sorted(records, key=lambda r: r.filename)],
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)
    return path


def acquire(
    raw_dir: Path,
    catalog_dir: Path,
    urls: list[str] | None = None,
    english_only: bool = True,
    user_directed: bool = False,
    fetcher: Optional[Fetcher] = None,
) -> list[ManualRecord]:
    """Download any new URLs, then index every PDF in `raw_dir` into a manifest.

    Re-running is cheap and safe: files already present are not re-downloaded,
    and content hashes deduplicate the same manual arriving under two names.
    """
    raw_dir, catalog_dir = Path(raw_dir), Path(catalog_dir)

    if urls:
        fetcher = fetcher or Fetcher(raw_dir, user_directed=user_directed)
        for url in urls:
            try:
                fetcher.fetch(url)
            except Exception as exc:
                log.error("Failed %s: %s", url, exc)

    by_hash = load_manifest(catalog_dir)
    known_names = {r.filename for r in by_hash.values()}
    url_by_name = {filename_for(u): u for u in (urls or [])}
    coverage = load_coverage(catalog_dir)

    for pdf in sorted(raw_dir.glob("*.pdf")):
        if pdf.name in known_names:
            continue
        try:
            record = build_record(
                pdf, url=url_by_name.get(pdf.name, ""), coverage=coverage
            )
        except Exception as exc:
            log.error("Could not read %s: %s", pdf.name, exc)
            continue

        if english_only and record.language != "en":
            log.info("Skipping %s (language=%s)", pdf.name, record.language)
            continue
        if record.sha256 in by_hash:
            log.info(
                "%s duplicates %s (same content) — keeping the first",
                pdf.name,
                by_hash[record.sha256].filename,
            )
            continue

        by_hash[record.sha256] = record
        log.info(
            "Indexed %s — %s, %d pages, %s",
            pdf.name,
            record.model,
            record.n_pages,
            record.os_version or "OS unknown",
        )

    records = list(by_hash.values())
    save_manifest(catalog_dir, records)
    log.info("Manifest: %d manuals", len(records))
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--urls", type=Path, help="file with one manual URL per line")
    parser.add_argument(
        "--scan", action="store_true", help="index PDFs already in data/raw"
    )
    parser.add_argument(
        "--user-directed",
        action="store_true",
        help="download URLs you collected yourself even where robots.txt disallows "
        "automated agents (Samsung's manual host disallows all)",
    )
    parser.add_argument("--all-languages", action="store_true")
    args = parser.parse_args(argv)

    settings = load_settings(require_api_key=False)
    setup_logging(settings.log_level)

    if not args.urls and not args.scan:
        parser.error("give --urls SOURCES.txt, or --scan to adopt local PDFs")

    urls = read_url_list(args.urls) if args.urls else []
    records = acquire(
        raw_dir=settings.raw_dir,
        catalog_dir=settings.catalog_dir,
        urls=urls,
        english_only=not args.all_languages,
        user_directed=args.user_directed,
    )
    print(f"{len(records)} manuals in {settings.catalog_dir / MANIFEST_NAME}")
    for r in records:
        print(f"  {r.model:24} {r.n_pages:4}p  {r.filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
