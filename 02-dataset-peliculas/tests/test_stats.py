from crawler.stats import DatasetStats, format_duration, format_film

PSYCHO = {
    "title": "Psycho",
    "year": 1960,
    "genres": "horror|thriller",
    "directors": "Alfred Hitchcock",
    "runtime_minutes": 109,
    "countries": "United States",
    "plot": "A secretary steals money.",
}
ALIEN_FROM_CSV = {
    "title": "Alien",
    "year": "1979",
    "genres": "horror|science fiction",
    "directors": "Ridley Scott",
    "runtime_minutes": "117",
    "countries": "",
    "plot": "",
}


def test_format_film_shows_interesting_details():
    assert format_film(PSYCHO, 12, 1000) == (
        "[12/1000] Psycho (1960) · horror, thriller · dir. Alfred Hitchcock"
        " · 109 min · United States"
    )


def test_format_film_omits_missing_details():
    row = {"title": "Unknown", "year": "", "genres": "drama", "runtime_minutes": ""}

    assert format_film(row, 1, 10) == "[1/10] Unknown · drama"


def test_stats_accept_new_records_and_csv_rows():
    stats = DatasetStats()
    stats.add(PSYCHO)
    stats.add(ALIEN_FROM_CSV)

    assert stats.count == 2
    assert stats.with_plot == 1
    assert stats.genres["horror"] == 2
    assert stats.decades == {1960: 1, 1970: 1}
    assert stats.oldest == (1960, "Psycho")
    assert stats.longest == (117, "Alien")


def test_summary_mentions_each_fact_once():
    stats = DatasetStats()
    stats.add(PSYCHO)
    stats.add(ALIEN_FROM_CSV)

    text = "\n".join(stats.summary_lines())

    assert "Géneros (3 distintos): horror 2" in text
    assert "Décadas: 1960s 1, 1970s 1" in text
    assert "con trama 50%" in text
    assert "más antigua: Psycho (1960)" in text
    assert "más larga: Alien (117 min)" in text
    assert text.count("Psycho") == 1


def test_summary_is_empty_without_films():
    assert DatasetStats().summary_lines() == []


def test_format_duration():
    assert format_duration(20) == "menos de 1 min"
    assert format_duration(600) == "10 min"
