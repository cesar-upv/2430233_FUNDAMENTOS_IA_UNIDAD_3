import pytest
import requests

from crawler.fetcher import (
    MAX_ATTEMPTS,
    MAX_CONSECUTIVE_FAILURES,
    CrawlAborted,
    PoliteFetcher,
    build_user_agent,
    parse_retry_after,
)

ROBOTS = "User-agent: *\nDisallow: /w/\nDisallow: /wiki/Special:\nCrawl-delay: 3\n"
PAGE = "https://en.wikipedia.org/wiki/Alien_(film)"


class FakeResponse:
    def __init__(self, status=200, text="<html></html>", headers=None):
        self.status_code = status
        self.text = text
        self.headers = {"Content-Type": "text/html; charset=UTF-8", **(headers or {})}


class FakeSession:
    def __init__(self, responses):
        self.headers = {}
        self.responses = list(responses)
        self.calls = []

    def get(self, url, timeout, allow_redirects):
        self.calls.append((url, allow_redirects))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def make_fetcher(page_responses, robots=ROBOTS, delay=1.0):
    clock = FakeClock()
    session = FakeSession([FakeResponse(text=robots), *page_responses])
    fetcher = PoliteFetcher(
        "user@example.org", delay=delay, session=session, sleep=clock.sleep, clock=clock.time
    )
    fetcher.load_robots()
    clock.sleeps.clear()
    return fetcher, session, clock


def test_user_agent_identifies_bot_and_contact():
    assert build_user_agent("user@example.org").startswith(
        "AiRecommenderBot/0.1 (class project; user@example.org) "
    )


def test_robots_blocks_disallowed_url_without_requesting_it():
    fetcher, session, _ = make_fetcher([])
    calls_before = len(session.calls)

    assert fetcher.get("https://en.wikipedia.org/w/index.php") is None
    assert len(session.calls) == calls_before


def test_robots_failure_aborts_crawl():
    session = FakeSession([FakeResponse(status=503)])
    fetcher = PoliteFetcher("c", session=session, sleep=lambda _: None)

    with pytest.raises(CrawlAborted):
        fetcher.load_robots()


def test_requires_robots_before_fetching():
    fetcher = PoliteFetcher("c", session=FakeSession([]), sleep=lambda _: None)

    with pytest.raises(RuntimeError):
        fetcher.get(PAGE)


def test_crawl_delay_from_robots_overrides_shorter_delay():
    fetcher, _, clock = make_fetcher([FakeResponse(), FakeResponse()], delay=1.0)

    fetcher.get(PAGE)
    fetcher.get(PAGE)

    assert clock.sleeps == [3.0, 3.0]


def test_configured_delay_wins_when_longer_than_crawl_delay():
    fetcher, _, clock = make_fetcher([FakeResponse()], robots="User-agent: *\nCrawl-delay: 1\n", delay=2.0)

    fetcher.get(PAGE)

    assert clock.sleeps == [2.0]


def test_429_waits_retry_after_then_succeeds():
    responses = [FakeResponse(status=429, headers={"Retry-After": "120"}), FakeResponse(text="ok")]
    fetcher, _, clock = make_fetcher(responses, robots="User-agent: *\nAllow: /\n")

    assert fetcher.get(PAGE) == "ok"
    assert 120 in clock.sleeps


def test_persistent_429_aborts():
    responses = [FakeResponse(status=429, headers={"Retry-After": "1"})] * MAX_ATTEMPTS
    fetcher, _, _ = make_fetcher(responses)

    with pytest.raises(CrawlAborted):
        fetcher.get(PAGE)


def test_excessive_retry_after_aborts():
    fetcher, _, _ = make_fetcher([FakeResponse(status=429, headers={"Retry-After": "86400"})])

    with pytest.raises(CrawlAborted):
        fetcher.get(PAGE)


def test_transient_error_is_retried():
    responses = [requests.ConnectionError("x"), FakeResponse(status=503), FakeResponse(text="ok")]
    fetcher, _, _ = make_fetcher(responses)

    assert fetcher.get(PAGE) == "ok"


def test_not_found_is_skipped_without_retry():
    fetcher, session, _ = make_fetcher([FakeResponse(status=404)])
    calls_before = len(session.calls)

    assert fetcher.get(PAGE) is None
    assert len(session.calls) == calls_before + 1


def test_redirects_are_not_followed():
    fetcher, session, _ = make_fetcher([FakeResponse(status=301, headers={"Location": "/w/x"})])

    assert fetcher.get(PAGE) is None
    assert session.calls[-1] == (PAGE, False)


def test_non_html_response_is_skipped():
    fetcher, _, _ = make_fetcher([FakeResponse(headers={"Content-Type": "application/json"})])

    assert fetcher.get(PAGE) is None


def test_consecutive_failed_pages_abort():
    responses = [FakeResponse(status=503)] * (MAX_ATTEMPTS * MAX_CONSECUTIVE_FAILURES)
    fetcher, _, _ = make_fetcher(responses)

    for _ in range(MAX_CONSECUTIVE_FAILURES - 1):
        assert fetcher.get(PAGE) is None
    with pytest.raises(CrawlAborted):
        fetcher.get(PAGE)


def test_parse_retry_after_handles_all_formats():
    assert parse_retry_after("30") == 30
    assert parse_retry_after("-5") == 0
    assert parse_retry_after("Wed, 21 Oct 2015 07:28:00 GMT") == 0
    assert parse_retry_after("not a date") is None
    assert parse_retry_after(None) is None
