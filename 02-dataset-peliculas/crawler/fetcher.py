"""Cliente HTTP respetuoso: robots.txt, ritmo limitado y manejo de errores 429."""

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.robotparser import RobotFileParser

import requests

logger = logging.getLogger(__name__)

BOT_NAME = "AiRecommenderBot"
BOT_VERSION = "0.1"
ROBOTS_URL = "https://en.wikipedia.org/robots.txt"
REQUEST_TIMEOUT = (10, 30)
MAX_ATTEMPTS = 5
MAX_RETRY_AFTER_SECONDS = 3600
MAX_CONSECUTIVE_FAILURES = 5
TRANSIENT_STATUS = {500, 502, 503, 504}


class CrawlAborted(Exception):
    """El servidor indica que debemos detenernos; el progreso se conserva."""


def build_user_agent(contact: str) -> str:
    """Construye el User-Agent con el formato de la política de Wikimedia."""
    return f"{BOT_NAME}/{BOT_VERSION} (class project; {contact}) requests/{requests.__version__}"


def parse_retry_after(value: str | None) -> float | None:
    """Interpreta `Retry-After`, que puede ser un número de segundos o una fecha HTTP."""
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        moment = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return max(0.0, (moment - datetime.now(UTC)).total_seconds())


class PoliteFetcher:
    """Descarga páginas de una en una, sin superar el ritmo configurado."""

    def __init__(
        self,
        contact: str,
        delay: float = 1.0,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._session = session or requests.Session()
        self._session.headers.update(
            {"User-Agent": build_user_agent(contact), "Accept-Encoding": "gzip"}
        )
        self._delay = delay
        self._sleep = sleep
        self._clock = clock
        self._last_request: float | None = None
        self._robots: RobotFileParser | None = None
        self._consecutive_failures = 0

    def load_robots(self) -> None:
        """Descarga robots.txt; sin esas reglas no es seguro continuar."""
        self._wait_turn()
        try:
            response = self._session.get(
                ROBOTS_URL, timeout=REQUEST_TIMEOUT, allow_redirects=False
            )
        except requests.RequestException as error:
            raise CrawlAborted(f"No se pudo descargar robots.txt: {error}") from error
        if response.status_code != 200:
            raise CrawlAborted(
                f"No se pudo descargar robots.txt (estado {response.status_code})."
            )
        robots = RobotFileParser()
        robots.parse(response.text.splitlines())
        self._robots = robots
        crawl_delay = robots.crawl_delay(BOT_NAME)
        if crawl_delay is not None:
            self._delay = max(self._delay, float(crawl_delay))

    def allowed(self, url: str) -> bool:
        if self._robots is None:
            raise RuntimeError("Hay que llamar a load_robots() antes de rastrear.")
        return self._robots.can_fetch(BOT_NAME, url)

    def get(self, url: str) -> str | None:
        """Devuelve el HTML, o None si la página se omite por reglas o errores."""
        if not self.allowed(url):
            logger.warning("robots.txt no permite esta URL; se omite: %s", url)
            return None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._wait_turn()
            try:
                response = self._session.get(
                    url, timeout=REQUEST_TIMEOUT, allow_redirects=False
                )
            except requests.RequestException as error:
                logger.warning("Error de conexión en %s: %s", url, error)
                self._backoff(attempt)
                continue

            status = response.status_code
            if status == 200:
                self._consecutive_failures = 0
                if "text/html" not in response.headers.get("Content-Type", ""):
                    logger.warning("La respuesta no es HTML; se omite: %s", url)
                    return None
                return response.text
            if status == 429:
                self._wait_retry_after(response, attempt)
                continue
            if status in TRANSIENT_STATUS:
                logger.warning("Estado %s en %s; se reintentará.", status, url)
                self._wait_after_server_error(response, attempt)
                continue

            logger.warning("Estado %s; se omite: %s", status, url)
            return None

        return self._register_failure(url)

    def _register_failure(self, url: str) -> None:
        self._consecutive_failures += 1
        logger.warning("Se agotaron los reintentos; se omite: %s", url)
        if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            raise CrawlAborted(
                f"Hubo {MAX_CONSECUTIVE_FAILURES} páginas seguidas con errores; "
                "se detiene el rastreo."
            )

    def _wait_turn(self) -> None:
        if self._last_request is not None:
            remaining = self._delay - (self._clock() - self._last_request)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request = self._clock()

    def _backoff(self, attempt: int) -> None:
        if attempt < MAX_ATTEMPTS:
            self._sleep(2.0**attempt)

    def _wait_after_server_error(self, response: requests.Response, attempt: int) -> None:
        retry_after = parse_retry_after(response.headers.get("Retry-After"))
        if retry_after is None:
            self._backoff(attempt)
        elif attempt < MAX_ATTEMPTS:
            self._sleep_requested(retry_after)

    def _wait_retry_after(self, response: requests.Response, attempt: int) -> None:
        if attempt == MAX_ATTEMPTS:
            raise CrawlAborted("El servidor sigue respondiendo 429; se detiene el rastreo.")
        retry_after = parse_retry_after(response.headers.get("Retry-After"))
        wait = retry_after if retry_after is not None else 2.0**attempt
        logger.warning("Estado 429; se esperarán %.0f s.", wait)
        self._sleep_requested(wait)

    def _sleep_requested(self, seconds: float) -> None:
        if seconds > MAX_RETRY_AFTER_SECONDS:
            raise CrawlAborted(
                f"El servidor pidió esperar {seconds:.0f} s; se detiene el rastreo."
            )
        self._sleep(seconds)
