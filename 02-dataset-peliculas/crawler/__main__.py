"""Interfaz de línea de comandos del crawler."""

import argparse
import logging
import os
import signal
import sys
from pathlib import Path

from crawler.crawl import CrawlSettings, crawl
from crawler.fetcher import CrawlAborted, PoliteFetcher
from crawler.parser import is_article_url, is_category_url, normalize_wiki_url

MIN_DELAY_SECONDS = 1.0
CONTACT_VARIABLE = "CRAWLER_CONTACT"

# Una película conocida por cada familia de géneros, para empezar con variedad.
DEFAULT_SEEDS = [
    "https://en.wikipedia.org/wiki/The_Shawshank_Redemption",
    "https://en.wikipedia.org/wiki/The_Matrix",
    "https://en.wikipedia.org/wiki/Toy_Story",
    "https://en.wikipedia.org/wiki/Alien_(film)",
    "https://en.wikipedia.org/wiki/Some_Like_It_Hot",
    "https://en.wikipedia.org/wiki/Casablanca_(film)",
    "https://en.wikipedia.org/wiki/Spirited_Away",
    "https://en.wikipedia.org/wiki/Psycho_(1960_film)",
    "https://en.wikipedia.org/wiki/Mad_Max:_Fury_Road",
    "https://en.wikipedia.org/wiki/La_La_Land",
    "https://en.wikipedia.org/wiki/Unforgiven",
    "https://en.wikipedia.org/wiki/Saving_Private_Ryan",
    "https://en.wikipedia.org/wiki/March_of_the_Penguins",
    "https://en.wikipedia.org/wiki/The_Lord_of_the_Rings:_The_Fellowship_of_the_Ring",
    "https://en.wikipedia.org/wiki/Rocky",
    "https://en.wikipedia.org/wiki/Seven_(1995_film)",
    "https://en.wikipedia.org/wiki/Parasite_(2019_film)",
    "https://en.wikipedia.org/wiki/Seven_Samurai",
]


def _seed_url(value: str) -> str:
    url = normalize_wiki_url(value)
    if url is None or not (is_article_url(url) or is_category_url(url)):
        raise argparse.ArgumentTypeError(
            "La semilla debe ser una URL https://en.wikipedia.org/wiki/... sin parámetros."
        )
    return url


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crawler",
        description="Crea un dataset CSV de películas a partir de Wikipedia en inglés.",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/movies.csv"), help="archivo CSV de salida"
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=Path("data/crawl_state.json"),
        help="archivo con el estado para reanudar",
    )
    parser.add_argument("--target", type=int, default=1000, help="máximo de películas")
    parser.add_argument(
        "--min-items", type=int, default=500, help="mínimo aceptable de películas"
    )
    parser.add_argument(
        "--max-requests", type=int, default=3000, help="máximo de peticiones del rastreo"
    )
    parser.add_argument(
        "--per-category", type=int, default=15, help="artículos a tomar de cada categoría"
    )
    parser.add_argument(
        "--delay", type=float, default=MIN_DELAY_SECONDS, help="segundos entre peticiones"
    )
    parser.add_argument("--random-seed", type=int, default=42, help="semilla del muestreo")
    parser.add_argument(
        "--seed",
        action="append",
        type=_seed_url,
        dest="seeds",
        help="URL inicial; se puede repetir",
    )
    parser.add_argument(
        "--resume", action="store_true", help="continúa un rastreo previo"
    )
    return parser


def _interrupt_on_terminate(_signum: int, _frame: object) -> None:
    """Trata SIGTERM como Ctrl+C para guardar el estado antes de salir."""
    raise KeyboardInterrupt


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    signal.signal(signal.SIGTERM, _interrupt_on_terminate)

    contact = os.environ.get(CONTACT_VARIABLE, "").strip()
    if not contact:
        parser.error(
            f"Define {CONTACT_VARIABLE} con un contacto; la política de Wikimedia lo solicita."
        )
    if args.delay < MIN_DELAY_SECONDS:
        parser.error(f"--delay debe ser de al menos {MIN_DELAY_SECONDS} s.")
    if not 1 <= args.min_items <= args.target:
        parser.error("Se requiere 1 <= --min-items <= --target.")
    if args.per_category < 1 or args.max_requests < 1:
        parser.error("--per-category y --max-requests deben ser positivos.")
    if not args.resume and (args.output.exists() or args.state.exists()):
        parser.error(
            f"Ya existe {args.output} o {args.state}. Usa --resume, o elige otras rutas."
        )

    fetcher = PoliteFetcher(contact, delay=args.delay)
    settings = CrawlSettings(
        output=args.output,
        state=args.state,
        target=args.target,
        max_requests=args.max_requests,
        per_category=args.per_category,
        random_seed=args.random_seed,
    )
    try:
        fetcher.load_robots()
        summary = crawl(fetcher, args.seeds or DEFAULT_SEEDS, settings, resume=args.resume)
    except CrawlAborted as error:
        logging.error("%s Reanuda después con --resume.", error)
        return 2
    except KeyboardInterrupt:
        logging.warning("Rastreo interrumpido. Reanuda después con --resume.")
        return 130

    logging.info("Rastreo terminado. Dataset guardado en %s.", args.output)
    if summary.items < args.min_items:
        logging.error(
            "El dataset quedó por debajo del mínimo: %d de %d películas.",
            summary.items,
            args.min_items,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
