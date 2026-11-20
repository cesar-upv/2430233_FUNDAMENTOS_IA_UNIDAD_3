"""Extracción de metadatos y enlaces desde el HTML de Wikipedia en inglés."""

import re
from dataclasses import asdict, dataclass
from urllib.parse import unquote, urldefrag, urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

BASE_URL = "https://en.wikipedia.org"
WIKI_PREFIX = "/wiki/"
CATEGORY_PREFIX = "Category:"
LIST_SEPARATOR = "|"

# Espacios de nombres de MediaWiki que no son artículos.
NON_ARTICLE_NAMESPACE = re.compile(
    r"^(?:File|Image|Help|Talk|Wikipedia|WP|Template|Portal|Special|User|Draft|Module"
    r"|MediaWiki|Book|TimedText|Category)(?:_talk)?:",
    re.IGNORECASE,
)

# Vocabulario canónico: cada género se reconoce por una expresión regular.
GENRE_PATTERNS = {
    "action": r"\baction\b",
    "adventure": r"\badventure\b",
    "animation": r"\banimat(?:ed|ion)\b|\banime\b",
    "biography": r"\bbiographical\b|\bbiopics?\b",
    "comedy": r"\bcomed(?:y|ies)\b|\bcomedic\b",
    "crime": r"\bcrime\b",
    "documentary": r"\bdocumentar(?:y|ies)\b",
    "drama": r"\bdramas?\b|\bdramatic\b|\bmelodramas?\b",
    "family": r"\bfamily\b(?!\s+drama)|\bchildren's\b",
    "fantasy": r"\bfantasy\b",
    "film noir": r"\bnoir\b",
    "historical": r"\bhistorical\b",
    "horror": r"\bhorror\b",
    "martial arts": r"\bmartial arts\b",
    "musical": r"\bmusical\b",
    "mystery": r"\bmystery\b",
    "romance": r"\bromantic\b|\bromance\b",
    "science fiction": r"\bscience[- ]fiction\b|\bsci-fi\b",
    "sports": r"\bsports?\b",
    "superhero": r"\bsuperhero\b",
    "thriller": r"\bthrillers?\b",
    "war": r"\bwar\b",
    "western": r"\bwesterns?\b(?!\s+(?:australia|europe|canad|africa|asia))",
}
_COMPILED_GENRES = {
    genre: re.compile(pattern, re.IGNORECASE) for genre, pattern in GENRE_PATTERNS.items()
}

_EXCLUDED_CATEGORY_WORDS = re.compile(
    r"\b(?:awards?|winning|winners?|nominated|best|lists?|stubs?|articles?|pages|wikipedia"
    r"|short|television|pornographic)\b",
    re.IGNORECASE,
)
_ADULT_CATEGORY = re.compile(r"\bpornograph(?:ic|y)\b", re.IGNORECASE)
_SUBJECT_DESCRIPTION = re.compile(r"\b(?:is|are)\s+(?:(?:an?|the)\s+)?(.{0,160})", re.IGNORECASE)
# La primera coincidencia es el sustantivo que define la obra: "is a short film"
# la excluye, pero "is a film based on the film series" no.
_SUBJECT_NOUN = re.compile(
    r"\b(film series|film franchise|media franchise|franchise|film trilogy|trilogy"
    r"|film serial|series of|television (?:film|movie)|tv (?:film|movie)|telefilm"
    r"|made-for-(?:television|tv)|short(?!-)|films?)\b",
    re.IGNORECASE,
)
_NON_FILM_TITLE = re.compile(
    r"\((?:[^()]*\s)?(?:film series|franchise|miniseries|mini-series|serial|tv series"
    r"|television series)\)$",
    re.IGNORECASE,
)
# Enlaces a otras ediciones de Wikipedia que aparecen junto a un nombre: "Nombre [de]".
_INTERLANGUAGE_LINK = re.compile(r"\s*\[[a-z]{2,3}(?:-[a-z]+)?\]")
# Umbral de la Academia para distinguir largometrajes de cortometrajes.
MIN_FEATURE_MINUTES = 40
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_LEAD_DESCRIPTION = re.compile(r"\b(?:is|was)\s+an?\s+(.{0,160}?)\bfilms?\b", re.IGNORECASE)
_PLOT_HEADING_ID = re.compile(r"^(?:plot|synopsis|premise|summary|story)(?:_|$)", re.IGNORECASE)
_DISAMBIGUATION = re.compile(r"\s*\([^()]*\bfilm\)$", re.IGNORECASE)
_YEAR_CATEGORY = re.compile(r"^(\d{4}) films$")
_YEAR = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")
_RUNTIME = re.compile(r"(\d+)\s*min", re.IGNORECASE)
_THEME_CATEGORY = re.compile(r"^Films about (.+)$")


@dataclass(frozen=True)
class FilmRecord:
    """Una fila del dataset; el orden de los campos define las columnas del CSV."""

    title: str
    year: int | None
    genres: str
    directors: str
    cast: str
    countries: str
    languages: str
    runtime_minutes: int | None
    themes: str
    summary: str
    plot: str
    url: str

    def to_row(self) -> dict[str, str | int | None]:
        return asdict(self)


@dataclass(frozen=True)
class FilmPage:
    """Resultado de analizar un artículo de película."""

    record: FilmRecord
    genre_list: tuple[str, ...]
    genre_category_urls: tuple[str, ...]


@dataclass(frozen=True)
class CategoryPage:
    """Enlaces descubiertos en una página de categoría."""

    article_urls: tuple[str, ...]
    subcategory_urls: tuple[str, ...]


def normalize_wiki_url(href: str, base: str = BASE_URL) -> str | None:
    """Devuelve una URL `https://en.wikipedia.org/wiki/...` sin parámetros, o None."""
    absolute, _fragment = urldefrag(urljoin(base, href))
    parts = urlsplit(absolute)
    is_wiki_path = parts.path.startswith(WIKI_PREFIX) and len(parts.path) > len(WIKI_PREFIX)
    if parts.scheme != "https" or parts.netloc != "en.wikipedia.org" or not is_wiki_path:
        return None
    if parts.query:
        return None
    return absolute


def wiki_title(url: str) -> str:
    """Obtiene el título decodificado de una URL de Wikipedia."""
    return unquote(urlsplit(url).path.removeprefix(WIKI_PREFIX))


def is_category_url(url: str) -> bool:
    return wiki_title(url).startswith(CATEGORY_PREFIX)


def is_article_url(url: str) -> bool:
    return NON_ARTICLE_NAMESPACE.match(wiki_title(url)) is None


def category_display_name(url: str) -> str:
    return wiki_title(url).removeprefix(CATEGORY_PREFIX).replace("_", " ")


def genres_in_text(text: str) -> list[str]:
    """Encuentra los géneros del vocabulario canónico dentro de un texto."""
    return [genre for genre, pattern in _COMPILED_GENRES.items() if pattern.search(text)]


def genres_from_category(name: str) -> list[str]:
    """Devuelve los géneros de una categoría de películas, o [] si no es de género."""
    lowered = name.casefold()
    if not lowered.endswith(" films") or lowered.startswith("films "):
        return []
    if _EXCLUDED_CATEGORY_WORDS.search(name):
        return []
    return genres_in_text(name)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _soup(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "lxml")
    for node in soup.select("sup, style, script, .mw-editsection"):
        node.decompose()
    return soup


def _content(soup: BeautifulSoup) -> Tag | None:
    return soup.select_one("#mw-content-text > .mw-parser-output")


def _lead(content: Tag) -> str:
    """Une los párrafos anteriores al primer encabezado del artículo.

    Wikipedia puede envolver cada sección en `<section>` (Parsoid) o dejar el
    contenido plano; por eso se admiten ambas estructuras.
    """
    first_section = content.find("section", recursive=False)
    container = first_section if first_section is not None else content
    paragraphs = []
    for child in container.find_all(recursive=False):
        if "mw-heading" in (child.get("class") or []):
            break
        if child.name == "p" and (text := _clean(child.get_text())):
            paragraphs.append(text)
    return " ".join(paragraphs)


def _section_paragraphs(heading_block: Tag) -> list[Tag]:
    """Obtiene los párrafos de una sección de nivel 2, incluidas sus subsecciones."""
    section = heading_block.parent
    if section is not None and section.name == "section":
        return [
            paragraph
            for paragraph in section.find_all("p")
            if not paragraph.find_parent(["table", "figure", "blockquote"])
        ]
    paragraphs = []
    for sibling in heading_block.find_next_siblings():
        if "mw-heading2" in (sibling.get("class") or []):
            break
        if sibling.name == "p":
            paragraphs.append(sibling)
    return paragraphs


def _plot(content: Tag) -> str:
    """Devuelve el texto de la sección de trama, o una cadena vacía si no existe."""
    for heading in content.select(".mw-heading2 > h2[id]"):
        if _PLOT_HEADING_ID.match(heading["id"]):
            texts = (_clean(p.get_text()) for p in _section_paragraphs(heading.parent))
            return " ".join(text for text in texts if text)
    return ""


def _infobox_rows(infobox: Tag) -> dict[str, Tag]:
    rows = {}
    for row in infobox.select("tr"):
        label = row.find("th", class_="infobox-label")
        cell = row.find("td", class_="infobox-data")
        if label is not None and cell is not None:
            rows[_clean(label.get_text()).casefold()] = cell
    return rows


def strip_interlanguage_links(text: str) -> str:
    return _INTERLANGUAGE_LINK.sub("", text)


def _cell_values(cell: Tag | None) -> list[str]:
    """Separa una celda del infobox en valores, por elementos de lista o saltos de línea."""
    if cell is None:
        return []
    items = [_clean(item.get_text()) for item in cell.select("li")]
    if not items:
        for line_break in cell.find_all("br"):
            line_break.replace_with("\n")
        items = [_clean(line) for line in cell.get_text().split("\n")]
    items = [strip_interlanguage_links(item) for item in items]
    return [item for item in dict.fromkeys(items) if item]


def _first_row(rows: dict[str, Tag], *labels: str) -> Tag | None:
    return next((rows[label] for label in labels if label in rows), None)


def _year(categories: list[str], release: Tag | None) -> int | None:
    for name in categories:
        if match := _YEAR_CATEGORY.match(name):
            return int(match.group(1))
    if release is not None and (match := _YEAR.search(release.get_text())):
        return int(match.group(1))
    return None


def _runtime(cell: Tag | None) -> int | None:
    if cell is not None and (match := _RUNTIME.search(cell.get_text())):
        return int(match.group(1))
    return None


def _canonical_url(soup: BeautifulSoup, fallback: str) -> str:
    link = soup.find("link", rel="canonical")
    href = link.get("href") if link else None
    return (normalize_wiki_url(href) if href else None) or fallback


def _describes_non_feature(summary: str) -> bool:
    """Indica si la primera frase presenta otra obra, no una película que la menciona."""
    first_sentence = _SENTENCE_END.split(summary, maxsplit=1)[0]
    subject = _SUBJECT_DESCRIPTION.search(first_sentence)
    noun = _SUBJECT_NOUN.search(subject.group(1)) if subject else None
    return noun is not None and noun.group(1).casefold() not in {"film", "films"}


def is_feature_film(title: str, summary: str, year: int | None, runtime: int | None) -> bool:
    """Excluye sagas, series, telefilmes, cortometrajes y obras sin año conocido."""
    if year is None or _NON_FILM_TITLE.search(title) or _describes_non_feature(summary):
        return False
    return runtime is None or runtime >= MIN_FEATURE_MINUTES


def _join(values: list[str]) -> str:
    return LIST_SEPARATOR.join(values)


def parse_film(html: str, url: str) -> FilmPage | None:
    """Analiza un artículo; devuelve None si no es una película con datos suficientes."""
    soup = _soup(html)
    content = _content(soup)
    heading = soup.select_one("#firstHeading")
    infobox = content.select_one("table.infobox") if content else None
    if content is None or heading is None or infobox is None:
        return None

    rows = _infobox_rows(infobox)
    category_links = soup.select("#mw-normal-catlinks ul a[href]")
    categories = [_clean(link.get_text()) for link in category_links]
    summary = _lead(content)

    is_film = (
        "directed by" in rows
        and "no. of episodes" not in rows
        and "no. of seasons" not in rows
        and any(re.search(r"\bfilms\b", name, re.IGNORECASE) for name in categories)
        and summary
        and not any(_ADULT_CATEGORY.search(name) for name in categories)
    )
    if not is_film:
        return None

    genre_urls = []
    found_genres = set()
    for link, name in zip(category_links, categories):
        if genres := genres_from_category(name):
            found_genres.update(genres)
            if category_url := normalize_wiki_url(link["href"]):
                genre_urls.append(category_url)
    if description := _LEAD_DESCRIPTION.search(summary):
        found_genres.update(genres_in_text(description.group(1)))
    if not found_genres:
        return None

    title = _DISAMBIGUATION.sub("", _clean(heading.get_text()))
    year = _year(categories, _first_row(rows, "release date", "release dates"))
    runtime = _runtime(rows.get("running time"))
    if not is_feature_film(title, summary, year, runtime):
        return None

    genre_list = tuple(sorted(found_genres))
    themes = [
        match.group(1) for name in categories if (match := _THEME_CATEGORY.match(name))
    ]
    record = FilmRecord(
        title=title,
        year=year,
        genres=_join(list(genre_list)),
        directors=_join(_cell_values(rows.get("directed by"))),
        cast=_join(_cell_values(rows.get("starring"))),
        countries=_join(_cell_values(_first_row(rows, "country", "countries"))),
        languages=_join(_cell_values(_first_row(rows, "language", "languages"))),
        runtime_minutes=runtime,
        themes=_join(themes),
        summary=summary,
        plot=_plot(content),
        url=_canonical_url(soup, url),
    )
    return FilmPage(
        record=record,
        genre_list=genre_list,
        genre_category_urls=tuple(dict.fromkeys(genre_urls)),
    )


def parse_category(html: str) -> CategoryPage:
    """Extrae artículos y subcategorías de género de una página de categoría."""
    soup = _soup(html)
    articles = []
    for link in soup.select("#mw-pages .mw-category a[href]"):
        url = normalize_wiki_url(link["href"])
        if url and is_article_url(url):
            articles.append(url)
    subcategories = []
    for link in soup.select("#mw-subcategories a[href]"):
        url = normalize_wiki_url(link["href"])
        if url and is_category_url(url) and genres_from_category(category_display_name(url)):
            subcategories.append(url)
    return CategoryPage(
        article_urls=tuple(dict.fromkeys(articles)),
        subcategory_urls=tuple(dict.fromkeys(subcategories)),
    )
