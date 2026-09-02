"""Discover manual PDF URLs for Galaxy phones, without crawling anything that
asks not to be crawled.

Samsung's setup is asymmetric, and the split matters:

* `www.samsung.com` publishes sitemaps in robots.txt and permits
  `/{region}/support/model/{SKU}/`. Those pages are server-rendered and contain
  the manual links. Discovery happens here, and it is explicitly sanctioned.
* `org.downloadcenter.samsung.com`, which serves the PDFs, is
  `User-agent: * / Disallow: /`. Nothing here fetches from it — this module only
  writes a list of URLs. Downloading them is a user-directed act, done by
  `ingest.acquire --user-directed`.

    python -m ingest.discover --series S --limit 12 -o sources.txt
"""

from __future__ import annotations

import argparse
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import unquote

import requests

from core.config import load_settings
from core.logging_setup import get_logger, setup_logging
from ingest.robots import USER_AGENT, RobotsCache

log = get_logger(__name__)

SITEMAP = "https://www.samsung.com/{region}/support/sitemap.xml"
MODEL_PAGE = "https://www.samsung.com/{region}/support/model/{sku}/"
DOWNLOAD_HOST = "https://org.downloadcenter.samsung.com/downloadfile/"

# Galaxy phone families, by the numeric block of the model code.
SERIES_PREFIXES = {
    "S": r"S9\d{2}",  # Galaxy S22-S25
    "G": r"G9\d{2}",  # Galaxy S8-S10 era (S10e is SM-G970)
    "FOLD": r"F9\d{2}",  # Galaxy Z Fold
    "FLIP": r"F7\d{2}",  # Galaxy Z Flip
    "A": r"A5\d{2}",  # Galaxy A5x
    "A0": r"A0\d{2}",  # Galaxy A0x budget line
    "A1": r"A1\d{2}",
    "A2": r"A2\d{2}",
    "A3": r"A3\d{2}",
}

_MODEL_URL_RE = re.compile(r"support/model/(SM-[A-Z0-9]+)", re.IGNORECASE)
_UM_LINK_RE = re.compile(r"ContentsFile\.aspx\?[^\"'\s<>]+", re.IGNORECASE)
_VPATH_RE = re.compile(r"VPath=([^&\"'\s]+)", re.IGNORECASE)
_DATE_RE = re.compile(r"UM/(\d{6})/")

# Documents that are not the user manual, and would dilute retrieval if indexed.
_NOT_A_MANUAL = re.compile(
    r"safety[_\s-]?information|quick[_\s-]?start|health|warranty", re.IGNORECASE
)

_ENGLISH = re.compile(r"_(ENG?|EN|UU)[_.]", re.IGNORECASE)


@dataclass
class ManualLink:
    sku: str
    base_code: str  # SM-S928W — the SKU without colour/carrier suffix
    url: str
    filename: str
    yyyymm: str
    covers: list[str] = field(default_factory=list)  # every model sharing this file

    def sort_key(self) -> str:
        return self.yyyymm

    def models(self) -> list[str]:
        return sorted(set(self.covers or [self.base_code]))


def base_code(sku: str) -> str:
    """SM-S928WZTFXAC -> SM-S928W. Colour and carrier suffixes are noise here."""
    match = re.match(r"(SM-[A-Z]\d{3}[A-Z]?)", sku.upper())
    return match.group(1) if match else sku.upper()


class Discoverer:
    def __init__(
        self,
        region: str = "ca",
        min_delay: float = 1.0,
        session: Optional[requests.Session] = None,
        robots: Optional[RobotsCache] = None,
        sleep=time.sleep,
        clock=time.monotonic,
    ):
        self.region = region
        self.min_delay = min_delay
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.robots = robots or RobotsCache()
        self._sleep = sleep
        self._clock = clock
        self._last: Optional[float] = None

    def _get(self, url: str) -> str:
        if not self.robots.allowed(url):
            raise PermissionError(f"robots.txt disallows {url}")
        if self._last is not None:
            delay = max(self.min_delay, self.robots.crawl_delay(url, self.min_delay))
            if (elapsed := self._clock() - self._last) < delay:
                self._sleep(delay - elapsed)
        self._last = self._clock()
        response = self.session.get(url, timeout=60)
        response.raise_for_status()
        return response.text

    def list_skus(
        self, series: Iterable[str] = (), codes: Iterable[str] = ()
    ) -> list[str]:
        """Read the support sitemap and return one SKU per distinct model.

        `codes` targets exact model codes (`G970`, `A155`) for devices that do
        not fall into a whole series worth crawling.
        """
        patterns = [SERIES_PREFIXES[s.upper()] for s in series]
        patterns += [re.escape(c.upper().removeprefix("SM-")) for c in codes]
        if not patterns:
            raise ValueError("give at least one series or model code")
        wanted = re.compile(rf"SM-({'|'.join(patterns)})[A-Z0-9]*", re.IGNORECASE)

        xml = self._get(SITEMAP.format(region=self.region))
        seen: dict[str, str] = {}
        for sku in _MODEL_URL_RE.findall(xml):
            sku = sku.upper()
            if not wanted.fullmatch(sku):
                continue
            seen.setdefault(base_code(sku), sku)  # first SKU per model is enough
        log.info("Sitemap: %d distinct models matched", len(seen))
        return [seen[k] for k in sorted(seen)]

    def manual_links(self, sku: str) -> list[ManualLink]:
        """Extract English user-manual links from one model's support page."""
        html = self._get(MODEL_PAGE.format(region=self.region, sku=sku))
        links: dict[str, ManualLink] = {}

        for raw in _UM_LINK_RE.findall(html):
            raw = raw.replace("&amp;", "&")
            if "CDCttType=UM" not in raw:
                continue
            vpath_match = _VPATH_RE.search(raw)
            if not vpath_match:
                continue
            vpath = unquote(vpath_match.group(1))
            filename = vpath.rsplit("/", 1)[-1]

            if _NOT_A_MANUAL.search(filename):
                continue
            if not _ENGLISH.search(filename):
                continue

            date_match = _DATE_RE.search(vpath)
            links[filename] = ManualLink(
                sku=sku,
                base_code=base_code(sku),
                url=DOWNLOAD_HOST + raw,
                filename=filename,
                yyyymm=date_match.group(1) if date_match else "000000",
            )
        return list(links.values())


def newest_per_model(links: Iterable[ManualLink]) -> list[ManualLink]:
    """Keep only the most recent manual per model.

    Samsung reissues a manual for each OS upgrade; indexing all of them would
    make the corpus contradict itself, and retrieval would surface whichever
    version happened to rank higher.
    """
    best: dict[str, ManualLink] = {}
    for link in links:
        current = best.get(link.base_code)
        if current is None or link.sort_key() > current.sort_key():
            best[link.base_code] = link
    return [best[k] for k in sorted(best)]


def dedupe_by_file(links: Iterable[ManualLink]) -> list[ManualLink]:
    """Collapse models that share one manual.

    Samsung ships a single combined manual per family generation — the S24 and
    S25 lines share `S93X_S92X_UG_...pdf`, so a per-model list asks for the same
    15 MB file eight times. Collapsing here keeps the download list honest and
    records which models the file actually covers, which the citation layer
    later needs to say "Galaxy S24/S25 series" rather than naming one phone.
    """
    by_file: dict[str, ManualLink] = {}
    for link in links:
        existing = by_file.get(link.filename)
        if existing is None:
            link.covers = [link.base_code]
            by_file[link.filename] = link
        else:
            existing.covers.append(link.base_code)
    return list(by_file.values())


def discover(
    series: Iterable[str] = (),
    region: str = "ca",
    limit: Optional[int] = None,
    discoverer: Optional[Discoverer] = None,
    codes: Iterable[str] = (),
) -> list[ManualLink]:
    discoverer = discoverer or Discoverer(region=region)
    skus = discoverer.list_skus(series, codes)
    if limit:
        skus = skus[-limit:]  # newest model codes sort last

    found: list[ManualLink] = []
    for sku in skus:
        try:
            links = discoverer.manual_links(sku)
        except Exception as exc:
            log.warning("%s: %s", sku, exc)
            continue
        if not links:
            log.info("%s: no English manual listed", sku)
            continue
        found.extend(links)
        log.info("%s: %d manual(s)", sku, len(links))

    return dedupe_by_file(newest_per_model(found))


def write_coverage(links: Iterable[ManualLink], path: Path, append: bool = False) -> Path:
    """Record filename -> model codes the manual actually covers.

    Filenames use wildcards (`S91X_S90X`, `A50X_A70X`) that cannot be resolved
    back to models by pattern-matching. Discovery already knows the answer
    exactly — it saw which SKU pages linked to this file — so it writes that
    down instead of leaving the acquirer to guess.
    """
    import json

    path = Path(path)
    payload: dict = {}
    if append and path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))

    for link in links:
        existing = payload.get(link.filename, {})
        merged = sorted(set(existing.get("model_codes", [])) | set(link.models()))
        payload[link.filename] = {"model_codes": merged, "yyyymm": link.yyyymm}

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def write_sources(links: Iterable[ManualLink], path: Path, append: bool = False) -> Path:
    path = Path(path)
    existing = path.read_text(encoding="utf-8").rstrip("\n") if append and path.exists() else ""
    already = {
        line.split("#", 1)[0].strip()
        for line in existing.splitlines()
        if line.split("#", 1)[0].strip()
    }

    lines = (
        [existing]
        if existing
        else ["# Generated by `python -m ingest.discover`. One manual URL per line."]
    )
    for link in links:
        if link.url in already:
            continue
        lines.append(
            f"\n# {link.filename}  ({link.yyyymm})\n# covers: {', '.join(link.models())}"
        )
        lines.append(link.url)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--series", nargs="+", default=[], choices=list(SERIES_PREFIXES) + ["s"],
        help="Galaxy families to include",
    )
    parser.add_argument(
        "--codes", nargs="+", default=[],
        help="exact model codes, e.g. G970 A155 A336",
    )
    parser.add_argument(
        "--replace", action="store_true",
        help="overwrite sources.txt / coverage.json instead of merging into them "
        "(default is to merge, so a narrow run cannot discard the wider corpus)",
    )
    parser.add_argument("--region", default="ca", help="Samsung site region (default: ca)")
    parser.add_argument("--limit", type=int, help="cap the number of models")
    parser.add_argument("-o", "--out", type=Path, default=Path("sources.txt"))
    args = parser.parse_args(argv)

    setup_logging("INFO")
    if not args.series and not args.codes:
        parser.error("give --series and/or --codes")

    links = discover(
        [s.upper() for s in args.series],
        region=args.region,
        limit=args.limit,
        codes=args.codes,
    )

    settings = load_settings(require_api_key=False)
    coverage_path = settings.catalog_dir / "coverage.json"
    write_sources(links, args.out, append=not args.replace)
    write_coverage(links, coverage_path, append=not args.replace)

    models = sum(len(l.models()) for l in links)
    print(f"\n{len(links)} manuals covering {models} models -> {args.out}\n")
    for link in links:
        print(f"  {link.yyyymm}  {link.filename}")
        print(f"            covers: {', '.join(link.models())}")
    print("\nNext: python -m ingest.acquire --urls sources.txt --user-directed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
