"""Ciclo del crawler: frontera de URLs, escritura del CSV y reanudación."""

import csv
import json
import logging
import os
import random
import time
from collections import Counter, deque
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Protocol

from crawler.parser import (
    FilmRecord,
    category_display_name,
    genres_from_category,
    is_category_url,
    parse_category,
    parse_film,
    wiki_title,
)
from crawler.stats import DatasetStats, format_duration, format_film

logger = logging.getLogger(__name__)

CSV_FIELDS = [field.name for field in fields(FilmRecord)]
STATE_SAVE_INTERVAL = 25
SUMMARY_INTERVAL = 50


class Fetcher(Protocol):
    def get(self, url: str) -> str | None: ...


@dataclass(frozen=True)
class CrawlSettings:
    output: Path
    state: Path
    target: int
    max_requests: int
    per_category: int
    random_seed: int


@dataclass(frozen=True)
class CrawlSummary:
    items: int
    requests: int
    rejected: int
    frontier_exhausted: bool


class Frontier:
    """URLs pendientes: primero artículos; después, la categoría del género menos cubierto."""

    def __init__(self, genre_counts: Counter[str]) -> None:
        self._articles: deque[str] = deque()
        self._categories: dict[str, list[str]] = {}
        self._genre_counts = genre_counts
        self.seen: set[str] = set()

    @property
    def pending_categories(self) -> int:
        return len(self._categories)

    def add_article(self, url: str) -> None:
        if url not in self.seen:
            self.seen.add(url)
            self._articles.append(url)

    def add_category(self, url: str) -> bool:
        if url in self.seen:
            return False
        self.seen.add(url)
        self._categories[url] = genres_from_category(category_display_name(url))
        return True

    def add_seed(self, url: str) -> None:
        if is_category_url(url):
            self.add_category(url)
        else:
            self.add_article(url)

    def pop(self) -> str | None:
        if self._articles:
            return self._articles.popleft()
        if not self._categories:
            return None
        url = min(self._categories, key=self._category_priority)
        del self._categories[url]
        return url

    def _category_priority(self, url: str) -> int:
        return min((self._genre_counts[g] for g in self._categories[url]), default=0)

    def snapshot(self) -> dict[str, list[str]]:
        return {
            "seen": sorted(self.seen),
            "articles": list(self._articles),
            "categories": list(self._categories),
        }

    def restore(self, data: dict[str, list[str]], saved_urls: set[str]) -> int:
        """Recupera la frontera sin las películas ya guardadas; devuelve cuántas omitió."""
        self.seen = set(data["seen"]) | saved_urls
        pending = [url for url in data["articles"] if url not in saved_urls]
        self._articles = deque(pending)
        self._categories = {
            url: genres_from_category(category_display_name(url)) for url in data["categories"]
        }
        return len(data["articles"]) - len(pending)


def _read_existing_dataset(path: Path, stats: DatasetStats) -> set[str]:
    urls: set[str] = set()
    if not path.exists():
        return urls
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("url") and row["url"] not in urls:
                urls.add(row["url"])
                stats.add(row)
    return urls


def _save_state(path: Path, frontier: Frontier, request_count: int, rejected: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    payload = {"requests": request_count, "rejected": rejected, "frontier": frontier.snapshot()}
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(temporary, path)


def _log_summary(
    stats: DatasetStats,
    target: int,
    request_count: int,
    rejected: int,
    frontier: Frontier,
    eta_seconds: float | None = None,
) -> None:
    header = (
        f"Resumen: {stats.count}/{target} películas ({stats.count * 100 // target}%) · "
        f"{request_count} peticiones · {rejected} descartadas · "
        f"{frontier.pending_categories} categorías pendientes"
    )
    if eta_seconds is not None:
        header += f" · tiempo restante aprox.: {format_duration(eta_seconds)}"
    logger.info(header)
    for line in stats.summary_lines():
        logger.info(line)


def crawl(
    fetcher: Fetcher,
    seeds: list[str],
    settings: CrawlSettings,
    resume: bool = False,
) -> CrawlSummary:
    """Ejecuta el rastreo hasta alcanzar la meta o agotar la frontera o el presupuesto."""
    stats = DatasetStats()
    accepted_urls = _read_existing_dataset(settings.output, stats)
    frontier = Frontier(stats.genres)
    request_count = 0
    rejected = 0

    if resume and settings.state.exists():
        saved = json.loads(settings.state.read_text(encoding="utf-8"))
        skipped = frontier.restore(saved["frontier"], accepted_urls)
        request_count = saved["requests"]
        rejected = saved.get("rejected", 0)
        logger.info(
            "Se reanuda el rastreo sin repetir %d películas guardadas (%d omitidas de la cola).",
            stats.count,
            skipped,
        )
        _log_summary(stats, settings.target, request_count, rejected, frontier)
    else:
        for seed in seeds:
            frontier.add_seed(seed)

    rng = random.Random(settings.random_seed + request_count)
    settings.output.parent.mkdir(parents=True, exist_ok=True)
    write_header = not settings.output.exists() or settings.output.stat().st_size == 0
    started = time.monotonic()
    initial_count = stats.count
    last_summary_count = stats.count

    with settings.output.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
            handle.flush()

        try:
            while stats.count < settings.target and request_count < settings.max_requests:
                url = frontier.pop()
                if url is None:
                    break
                html = fetcher.get(url)
                request_count += 1

                if html is not None:
                    if is_category_url(url):
                        _expand_category(url, html, frontier, settings.per_category, rng)
                    else:
                        page = parse_film(html, url)
                        if page is None:
                            rejected += 1
                            logger.info("Descartada: %s (no es película o le faltan datos)", _name(url))
                        elif page.record.url in accepted_urls:
                            rejected += 1
                            logger.info("Descartada: %s (ya está en el dataset)", _name(url))
                        else:
                            row = page.record.to_row()
                            writer.writerow(row)
                            handle.flush()
                            accepted_urls.add(page.record.url)
                            stats.add(row)
                            logger.info(format_film(row, stats.count, settings.target))
                            for category_url in page.genre_category_urls:
                                frontier.add_category(category_url)

                            if stats.count % SUMMARY_INTERVAL == 0:
                                added = stats.count - initial_count
                                seconds_per_film = (time.monotonic() - started) / added
                                _log_summary(
                                    stats,
                                    settings.target,
                                    request_count,
                                    rejected,
                                    frontier,
                                    (settings.target - stats.count) * seconds_per_film,
                                )
                                last_summary_count = stats.count

                if request_count % STATE_SAVE_INTERVAL == 0:
                    _save_state(settings.state, frontier, request_count, rejected)
        finally:
            _save_state(settings.state, frontier, request_count, rejected)

    if stats.count != last_summary_count:
        _log_summary(stats, settings.target, request_count, rejected, frontier)

    return CrawlSummary(
        items=stats.count,
        requests=request_count,
        rejected=rejected,
        frontier_exhausted=frontier.pop() is None,
    )


def _name(url: str) -> str:
    return wiki_title(url).replace("_", " ")


def _expand_category(
    url: str, html: str, frontier: Frontier, per_category: int, rng: random.Random
) -> None:
    """Agrega subcategorías y una muestra aleatoria para reducir el sesgo alfabético."""
    page = parse_category(html)
    new_subcategories = sum(frontier.add_category(sub) for sub in page.subcategory_urls)
    candidates = [article for article in page.article_urls if article not in frontier.seen]
    sample = rng.sample(candidates, k=min(per_category, len(candidates)))
    for article in sample:
        frontier.add_article(article)
    logger.info(
        "Categoría: %s → %d títulos en cola de %d nuevos · %d subcategorías nuevas",
        category_display_name(url),
        len(sample),
        len(candidates),
        new_subcategories,
    )
