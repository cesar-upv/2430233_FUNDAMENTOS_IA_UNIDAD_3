"""Estadísticas acumuladas del dataset y formato de los mensajes del log."""

from collections import Counter
from collections.abc import Mapping

from crawler.parser import LIST_SEPARATOR

TOP_GENRES = 6
SECONDS_PER_MINUTE = 60


def _values(row: Mapping[str, object], column: str) -> list[str]:
    return [value for value in str(row.get(column) or "").split(LIST_SEPARATOR) if value]


def _integer(row: Mapping[str, object], column: str) -> int | None:
    value = row.get(column)
    return int(value) if value not in (None, "") else None


def format_film(row: Mapping[str, object], count: int, target: int) -> str:
    """Describe en una línea una película recién agregada; omite los datos faltantes."""
    title = str(row["title"])
    year = _integer(row, "year")
    runtime = _integer(row, "runtime_minutes")
    directors = _values(row, "directors")
    countries = _values(row, "countries")
    parts = [
        f"{title} ({year})" if year else title,
        ", ".join(_values(row, "genres")),
        f"dir. {', '.join(directors)}" if directors else "",
        f"{runtime} min" if runtime else "",
        ", ".join(countries),
    ]
    return f"[{count}/{target}] " + " · ".join(part for part in parts if part)


def format_duration(seconds: float) -> str:
    minutes = round(seconds / SECONDS_PER_MINUTE)
    return f"{minutes} min" if minutes >= 1 else "menos de 1 min"


class DatasetStats:
    """Resume lo que ya contiene el dataset, tanto lo previo como lo nuevo."""

    def __init__(self) -> None:
        self.count = 0
        self.with_plot = 0
        self.genres: Counter[str] = Counter()
        self.decades: Counter[int] = Counter()
        self.directors: Counter[str] = Counter()
        self.oldest: tuple[int, str] | None = None
        self.longest: tuple[int, str] | None = None

    def add(self, row: Mapping[str, object]) -> None:
        title = str(row.get("title") or "")
        self.count += 1
        self.with_plot += bool(row.get("plot"))
        self.genres.update(_values(row, "genres"))
        self.directors.update(_values(row, "directors"))
        if (year := _integer(row, "year")) is not None:
            self.decades[year // 10 * 10] += 1
            if self.oldest is None or year < self.oldest[0]:
                self.oldest = (year, title)
        runtime = _integer(row, "runtime_minutes")
        if runtime is not None and (self.longest is None or runtime > self.longest[0]):
            self.longest = (runtime, title)

    def summary_lines(self) -> list[str]:
        """Genera el resumen; cada dato aparece una sola vez."""
        if self.count == 0:
            return []
        lines = []
        if self.genres:
            top = ", ".join(f"{g} {n}" for g, n in self.genres.most_common(TOP_GENRES))
            lines.append(f"  Géneros ({len(self.genres)} distintos): {top}")
        if self.decades:
            decades = ", ".join(f"{d}s {n}" for d, n in sorted(self.decades.items()))
            lines.append(f"  Décadas: {decades}")
        highlights = [f"con trama {self.with_plot * 100 // self.count}%"]
        if self.oldest:
            highlights.append(f"más antigua: {self.oldest[1]} ({self.oldest[0]})")
        if self.longest:
            highlights.append(f"más larga: {self.longest[1]} ({self.longest[0]} min)")
        if self.directors:
            director, films = self.directors.most_common(1)[0]
            highlights.append(f"director más frecuente: {director} ({films})")
        lines.append("  " + " · ".join(highlights))
        return lines
