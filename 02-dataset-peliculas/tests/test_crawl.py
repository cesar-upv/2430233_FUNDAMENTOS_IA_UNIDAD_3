import csv
import json
import logging
from collections import Counter

import pytest

from crawler.crawl import CSV_FIELDS, CrawlSettings, Frontier, crawl
from crawler.fetcher import CrawlAborted

BASE = "https://en.wikipedia.org/wiki/"
DRAMA = f"{BASE}Category:American_drama_films"
HORROR = f"{BASE}Category:American_horror_films"


def film(title, canonical=None, category=DRAMA):
    name = category.removeprefix(f"{BASE}Category:").replace("_", " ")
    return f"""
    <html><head><link rel="canonical" href="{BASE}{canonical or title}"></head><body>
    <h1 id="firstHeading">{title}</h1>
    <div id="mw-content-text"><div class="mw-parser-output">
      <table class="infobox vevent"><tr><th class="infobox-label">Directed by</th>
        <td class="infobox-data">Someone</td></tr></table>
      <p>{title} is a 2001 film.</p>
    </div></div>
    <div id="mw-normal-catlinks"><ul>
      <li><a href="/wiki/Category:2001_films">2001 films</a></li>
      <li><a href="/wiki/Category:{category.removeprefix(f"{BASE}Category:")}">{name}</a></li>
    </ul></div></body></html>
    """


def category(*titles):
    links = "".join(f'<a href="/wiki/{title}">{title}</a>' for title in titles)
    return f'<div id="mw-pages"><div class="mw-category">{links}</div></div>'


class FakeFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.requested = []

    def get(self, url):
        self.requested.append(url)
        page = self.pages.get(url)
        if isinstance(page, Exception):
            raise page
        return page


@pytest.fixture
def settings(tmp_path):
    return CrawlSettings(
        output=tmp_path / "out" / "movies.csv",
        state=tmp_path / "state.json",
        target=3,
        max_requests=50,
        per_category=10,
        random_seed=1,
    )


def rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_crawl_follows_links_from_seed_through_category(settings):
    fetcher = FakeFetcher(
        {
            f"{BASE}Seed": film("Seed"),
            DRAMA: category("Seed", "Second", "Third", "Fourth"),
            f"{BASE}Second": film("Second"),
            f"{BASE}Third": film("Third"),
            f"{BASE}Fourth": film("Fourth"),
        }
    )

    summary = crawl(fetcher, [f"{BASE}Seed"], settings)

    assert summary.items == 3
    assert [row["title"] for row in rows(settings.output)][0] == "Seed"
    assert len(rows(settings.output)) == 3
    assert fetcher.requested[:2] == [f"{BASE}Seed", DRAMA]
    assert fetcher.requested.count(f"{BASE}Seed") == 1


def test_crawl_deduplicates_by_canonical_url(settings):
    fetcher = FakeFetcher(
        {
            f"{BASE}Seed": film("Seed"),
            DRAMA: category("Redirected"),
            f"{BASE}Redirected": film("Seed", canonical="Seed"),
        }
    )

    summary = crawl(fetcher, [f"{BASE}Seed"], settings)

    assert summary.items == 1
    assert summary.rejected == 1
    assert summary.frontier_exhausted


def test_crawl_respects_request_budget(tmp_path):
    limited = CrawlSettings(
        output=tmp_path / "m.csv",
        state=tmp_path / "s.json",
        target=100,
        max_requests=2,
        per_category=10,
        random_seed=1,
    )
    fetcher = FakeFetcher(
        {f"{BASE}Seed": film("Seed"), DRAMA: category("A", "B"), f"{BASE}A": film("A")}
    )

    summary = crawl(fetcher, [f"{BASE}Seed"], limited)

    assert summary.requests == 2
    assert len(fetcher.requested) == 2


def test_crawl_limits_articles_per_category(tmp_path):
    limited = CrawlSettings(
        output=tmp_path / "m.csv",
        state=tmp_path / "s.json",
        target=100,
        max_requests=100,
        per_category=2,
        random_seed=1,
    )
    titles = [f"T{number}" for number in range(10)]
    pages = {f"{BASE}{title}": film(title) for title in titles}
    pages[DRAMA] = category(*titles)
    fetcher = FakeFetcher(pages)

    summary = crawl(fetcher, [DRAMA], limited)

    assert summary.items == 2


def test_crawl_resumes_without_repeating_work(settings):
    pages = {
        f"{BASE}Seed": film("Seed"),
        DRAMA: category("Second", "Third", "Fourth"),
        f"{BASE}Second": RuntimeError("corte"),
    }
    first = FakeFetcher(pages)
    with pytest.raises(RuntimeError):
        crawl(first, [f"{BASE}Seed"], settings)
    assert len(rows(settings.output)) == 1

    pages_second = {f"{BASE}{title}": film(title) for title in ("Second", "Third", "Fourth")}
    second = FakeFetcher(pages_second)
    summary = crawl(second, [f"{BASE}Seed"], settings, resume=True)

    assert summary.items == 3
    assert f"{BASE}Seed" not in second.requested
    assert len(rows(settings.output)) == 3
    assert len({row["url"] for row in rows(settings.output)}) == 3


def test_resume_does_not_request_films_saved_after_last_state(settings):
    """Reproduce una parada entre guardados: el CSV va adelantado respecto al estado."""
    settings.output.parent.mkdir(parents=True, exist_ok=True)
    with settings.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerow({"title": "Saved", "genres": "drama", "url": f"{BASE}Saved"})
    state = {
        "requests": 7,
        "rejected": 2,
        "frontier": {
            "seen": [f"{BASE}Pending", f"{BASE}Saved"],
            "articles": [f"{BASE}Saved", f"{BASE}Pending"],
            "categories": [],
        },
    }
    settings.state.write_text(json.dumps(state), encoding="utf-8")
    fetcher = FakeFetcher({f"{BASE}Pending": film("Pending")})

    summary = crawl(fetcher, [], settings, resume=True)

    assert f"{BASE}Saved" not in fetcher.requested
    assert fetcher.requested[0] == f"{BASE}Pending"
    assert summary.items == 2
    assert summary.requests == 7 + len(fetcher.requested)
    assert summary.rejected == 2


def test_crawl_logs_each_film_once_with_its_details(settings, caplog):
    fetcher = FakeFetcher({f"{BASE}Seed": film("Seed"), DRAMA: category("Seed")})

    with caplog.at_level(logging.INFO):
        crawl(fetcher, [f"{BASE}Seed"], settings)

    film_lines = [message for message in caplog.messages if message.startswith("[")]
    assert film_lines == ["[1/3] Seed (2001) · drama · dir. Someone"]


def test_crawl_logs_discard_reason(settings, caplog):
    fetcher = FakeFetcher(
        {
            f"{BASE}Seed": film("Seed"),
            DRAMA: category("Redirected", "Not_a_film"),
            f"{BASE}Redirected": film("Seed", canonical="Seed"),
            f"{BASE}Not_a_film": "<html></html>",
        }
    )

    with caplog.at_level(logging.INFO):
        crawl(fetcher, [f"{BASE}Seed"], settings)

    assert "Descartada: Redirected (ya está en el dataset)" in caplog.messages
    assert "Descartada: Not a film (no es película o le faltan datos)" in caplog.messages


def test_crawl_saves_state_when_server_aborts(settings):
    fetcher = FakeFetcher({f"{BASE}Seed": CrawlAborted("429")})

    with pytest.raises(CrawlAborted):
        crawl(fetcher, [f"{BASE}Seed"], settings)

    assert settings.state.exists()


def test_frontier_prefers_articles_then_least_covered_genre():
    counts = Counter({"drama": 10, "horror": 1})
    frontier = Frontier(counts)
    frontier.add_category(DRAMA)
    frontier.add_category(HORROR)
    frontier.add_article(f"{BASE}Film")

    assert frontier.pop() == f"{BASE}Film"
    assert frontier.pop() == HORROR
    assert frontier.pop() == DRAMA
    assert frontier.pop() is None


def test_frontier_ignores_repeated_urls():
    frontier = Frontier(Counter())
    frontier.add_article(f"{BASE}Film")
    frontier.add_article(f"{BASE}Film")

    assert frontier.pop() == f"{BASE}Film"
    assert frontier.pop() is None
