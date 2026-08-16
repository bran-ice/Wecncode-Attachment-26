"""Regression cover for robots handling.

`RobotFileParser.read()` fetches with urllib's default User-Agent, which Samsung
answers with 403 — and robotparser converts a 403 into "disallow everything".
The symptom is the worst kind: the crawler politely does nothing, and the log
line looks like Samsung asked it not to.
"""

import pytest

from ingest.robots import USER_AGENT, RobotsCache

SAMSUNG_LIKE = """User-agent: *
User-agent: Googlebot
Disallow:
Disallow: /*/search/
Disallow: /us/api/
Allow: /uk/info/contactus/email-the-ceo/

User-Agent: Sitereport
Disallow: /
"""

DENY_ALL = "User-agent: *\nDisallow: /\n"


class FakeResponse:
    def __init__(self, text="", status=200):
        self.text = text
        self.status_code = status


class FakeSession:
    def __init__(self, bodies: dict):
        self.bodies = bodies
        self.seen_headers: list[dict] = []

    def get(self, url, timeout=None, headers=None):
        self.seen_headers.append(headers or {})
        return self.bodies[url]


def cache(bodies):
    return RobotsCache(session=FakeSession(bodies))


def test_uses_our_user_agent_to_fetch_robots():
    session = FakeSession({"https://www.samsung.com/robots.txt": FakeResponse(SAMSUNG_LIKE)})
    RobotsCache(session=session).allowed("https://www.samsung.com/ca/")
    assert session.seen_headers[0]["User-Agent"] == USER_AGENT


def test_stacked_user_agent_group_is_parsed_not_treated_as_deny_all():
    r = cache({"https://www.samsung.com/robots.txt": FakeResponse(SAMSUNG_LIKE)})
    assert r.allowed("https://www.samsung.com/ca/support/sitemap.xml")
    assert r.allowed("https://www.samsung.com/ca/support/model/SM-S928WZTFXAC/")


def test_disallowed_paths_still_denied():
    r = cache({"https://www.samsung.com/robots.txt": FakeResponse(SAMSUNG_LIKE)})
    assert not r.allowed("https://www.samsung.com/us/search/")


def test_deny_all_host_is_denied():
    r = cache({"https://downloadcenter.samsung.com/robots.txt": FakeResponse(DENY_ALL)})
    assert not r.allowed("https://downloadcenter.samsung.com/content/UM/a.pdf")


def test_403_on_robots_is_treated_as_disallowed_not_as_allowed():
    r = cache({"https://x.com/robots.txt": FakeResponse("", 403)})
    assert not r.allowed("https://x.com/page")


def test_404_robots_means_no_restrictions():
    r = cache({"https://x.com/robots.txt": FakeResponse("", 404)})
    assert r.allowed("https://x.com/page")


def test_robots_fetched_once_per_host():
    session = FakeSession({"https://x.com/robots.txt": FakeResponse(SAMSUNG_LIKE)})
    r = RobotsCache(session=session)
    for _ in range(4):
        r.allowed("https://x.com/a")
    assert len(session.seen_headers) == 1


@pytest.mark.live
def test_live_samsung_robots_distinguishes_hosts():
    """Guards against Samsung changing its policy under us."""
    r = RobotsCache()
    assert r.allowed("https://www.samsung.com/ca/support/sitemap.xml")
    assert not r.allowed("https://org.downloadcenter.samsung.com/downloadfile/x.pdf")
