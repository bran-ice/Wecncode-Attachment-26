"""robots.txt checking.

Samsung disallows all automated agents on the host that serves manuals:

    downloadcenter.samsung.com/robots.txt
    User-agent: *
    Disallow: /

So this project does not crawl. It downloads a list of URLs the user collected
themselves, which is why `Fetcher` requires an explicit `user_directed=True` to
retrieve a robots-disallowed URL — the decision is recorded in code rather than
quietly assumed.
"""

from __future__ import annotations

import urllib.robotparser
from urllib.parse import urlparse

from core.logging_setup import get_logger

log = get_logger(__name__)

USER_AGENT = "samsung-manual-rag/0.1 (personal research project)"


class RobotsCache:
    """Fetches and caches one robots.txt per host."""

    def __init__(self, user_agent: str = USER_AGENT, session=None):
        self.user_agent = user_agent
        self.session = session
        self._parsers: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def _fetch(self, robots_url: str) -> str:
        # Deliberately not RobotFileParser.read(): it fetches with urllib's
        # default User-Agent, which Samsung answers with 403. robotparser turns
        # a 403 into "disallow everything", so every URL silently looked
        # forbidden — including pages robots.txt plainly allows.
        import requests

        session = self.session or requests
        response = session.get(
            robots_url, timeout=30, headers={"User-Agent": self.user_agent}
        )
        if response.status_code in (401, 403):
            raise PermissionError(f"{robots_url} returned {response.status_code}")
        if response.status_code >= 400:
            return ""  # 404 means no restrictions published
        return response.text

    def _parser(self, url: str):
        parts = urlparse(url)
        host = parts.netloc
        if host not in self._parsers:
            robots_url = f"{parts.scheme}://{host}/robots.txt"
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(robots_url)
            try:
                parser.parse(self._fetch(robots_url).splitlines())
            except Exception as exc:
                # Unreachable robots.txt is not permission to crawl, but it also
                # shouldn't hard-fail a user-directed download; caller decides.
                log.warning("Could not read %s (%s)", robots_url, exc)
                self._parsers[host] = None
                return None
            self._parsers[host] = parser
        return self._parsers[host]

    def allowed(self, url: str) -> bool:
        parser = self._parser(url)
        if parser is None:
            return False
        return parser.can_fetch(self.user_agent, url)

    def crawl_delay(self, url: str, default: float = 1.0) -> float:
        parser = self._parser(url)
        if parser is None:
            return default
        delay = parser.crawl_delay(self.user_agent)
        return float(delay) if delay else default
