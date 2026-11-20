<img src="assets/icon.svg" width="64" height="64" alt="">

# ai-recommender

Created in [T3 Code](https://t3.codes).

Proyecto de la clase **Fundamentos de IA**: un recomendador de medios construido por fases.
Este repositorio cubre hasta ahora la **fase 1: creación del dataset**, mediante un web crawler
que obtiene entre 500 y 1000 películas de la Wikipedia en inglés.

## Por qué Wikipedia

La intención inicial era usar IMDb o RateYourMusic, pero las condiciones revisadas el
2026-11-06 lo impiden o lo desaconsejan:

| Fuente | Motivo por el que no se usa |
|---|---|
| IMDb | `robots.txt` con `Disallow: /` para bots genéricos; sus condiciones prohíben el scraping sin consentimiento escrito. |
| RateYourMusic | `robots.txt` con `Disallow: /` para bots genéricos y prohibición expresa del acceso automatizado sin permiso. |
| API de TMDB | Sus términos prohíben usarla con aplicaciones basadas en ML o IA. |

## Cómo funciona

| Paso de la actividad | Implementación |
|---|---|
| 1. Dirección HTTPS | 18 películas semilla de géneros variados en `crawler/__main__.py`, o `--seed`. |
| 2. Obtener el HTML | `PoliteFetcher` en `crawler/fetcher.py`. |
| 3. Extraer metadatos | `parse_film` en `crawler/parser.py`. |
| 4. Enviar a un CSV | `crawl` en `crawler/crawl.py` escribe cada fila en cuanto se obtiene. |
| 5. Extraer otras URLs | Del artículo se siguen sus categorías de género; de la categoría, otras películas y subcategorías. |
| 6. Repetir | `Frontier` procesa los artículos y luego la categoría del género con menos películas. |

Wikipedia no muestra más de 200 títulos por página de categoría, y su paginación está en una ruta
prohibida por `robots.txt`. Por eso cada categoría aporta una muestra aleatoria de 15 títulos
como máximo, lo que reduce el sesgo alfabético de esos listados sin eliminarlo por completo.

## Límites de peticiones respetados

Reglas tomadas de `robots.txt` y de la
[política para robots de Wikimedia](https://wikitech.wikimedia.org/wiki/Robot_policy):

- Se consulta `robots.txt` antes de cada URL; si no se puede descargar, el rastreo no empieza.
- Solo se piden URLs `/wiki/Titulo` sin parámetros y no se siguen redirecciones.
- Una petición a la vez, con al menos 1 s entre peticiones. La política pide menos de 20 por
  segundo de media y menos de 10 simultáneas.
- El User-Agent identifica al bot e incluye un contacto, y se envía `Accept-Encoding: gzip`.
- Ante un 429 se espera lo que indique `Retry-After`. Si los errores persisten, el rastreo se
  detiene y se puede reanudar.

## Uso

Requiere [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env    # define CRAWLER_CONTACT con tu contacto
uv run --env-file .env python -m crawler
uv run --env-file .env python -m crawler --resume    # continúa un rastreo interrumpido
uv run pytest
```

El comando no sobrescribe un dataset existente, y `--resume` no vuelve a pedir las películas ya
guardadas en el CSV. Consulta todas las opciones con `uv run python -m crawler --help`.

### Log

Cada película agregada genera una línea con sus datos, y cada 50 películas aparece un resumen:

```text
14:12:25 INFO [1000/1000] Zack Snyder's Justice League (2021) · action, adventure, science fiction, superhero, thriller · dir. Zack Snyder · 242 min · United States
14:12:25 INFO Resumen: 1000/1000 películas (100%) · 1162 peticiones · 83 descartadas · 2700 categorías pendientes · tiempo restante aprox.: menos de 1 min
14:12:25 INFO   Géneros (23 distintos): drama 388, comedy 270, action 243, science fiction 129, romance 129, crime 124
14:12:25 INFO   Décadas: 1910s 2, 1920s 7, 1930s 36, 1940s 58, 1950s 47, 1960s 40, 1970s 99, 1980s 54, 1990s 165, 2000s 163, 2010s 222, 2020s 107
14:12:25 INFO   con trama 88% · más antigua: The Captive (1915) · más larga: 1900 (317 min) · director más frecuente: H. Bruce Humberstone (3)
```

Para guardar y seguir el log, ejecuta esto en dos terminales:

```bash
uv run --env-file .env python -m crawler --resume >> data/crawl.log 2>&1
tail -f data/crawl.log
```

## Dataset

El resultado está en `data/movies.csv`, en UTF-8. Los campos con varios valores se separan con `|`.

| Columna | Contenido |
|---|---|
| `title` | Título, sin la aclaración `(1994 film)`. |
| `year` | Año de estreno. |
| `genres` | Géneros normalizados a un vocabulario propio. |
| `directors`, `cast` | Dirección y reparto principal. |
| `countries`, `languages` | Países e idiomas. |
| `runtime_minutes` | Duración en minutos. |
| `themes` | Temas, a partir de las categorías `Films about ...`. |
| `summary` | Introducción del artículo. |
| `plot` | Trama; vacía si el artículo no tiene esa sección. |
| `url` | Artículo de origen, que sirve como atribución. |

Wikipedia no tiene un campo de género en la ficha de las películas. Los géneros se deducen de las
categorías y de la primera frase del artículo, así que pueden contener errores.

Solo se conservan largometrajes con año conocido. Se excluyen las obras que el artículo presenta
como saga, serial, serie, telefilme o cortometraje, las que duran menos de 40 minutos y las que
tienen categorías pornográficas. Estos filtros se basan en reglas de texto, por lo que algún caso
podría escapar.

El muestreo prioriza los géneros menos cubiertos para equilibrarlos, de modo que el dataset no
refleja la distribución real de la producción cinematográfica. Además, una película cuenta en todos
sus géneros, así que los totales por género suman más que el número de filas.

## Licencia de los datos

El texto de `data/movies.csv` proviene de [Wikipedia](https://en.wikipedia.org/) y se distribuye
bajo [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Los autores se acreditan
mediante el enlace de la columna `url`. El contenido fue modificado: se extrajeron fragmentos, se
quitaron las referencias y se normalizaron los espacios y los géneros.
