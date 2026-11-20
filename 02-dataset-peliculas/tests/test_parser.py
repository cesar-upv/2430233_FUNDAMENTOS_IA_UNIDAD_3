import pytest

from crawler.parser import (
    genres_from_category,
    is_article_url,
    is_feature_film,
    normalize_wiki_url,
    parse_category,
    parse_film,
)

FILM_URL = "https://en.wikipedia.org/wiki/Example_(1994_film)"


def film_html(infobox_extra="", lead="<p>Example is a 1994 American horror film.</p>", cats=None):
    categories = cats or [
        ("1994 films", "/wiki/Category:1994_films"),
        ("American crime drama films", "/wiki/Category:American_crime_drama_films"),
        ("Films about friendship", "/wiki/Category:Films_about_friendship"),
        ("Films set in Maine", "/wiki/Category:Films_set_in_Maine"),
    ]
    links = "".join(f'<li><a href="{href}">{name}</a></li>' for name, href in categories)
    return f"""
    <html><head><link rel="canonical" href="https://en.wikipedia.org/wiki/Example_(1994_film)">
    </head><body>
    <h1 id="firstHeading">Example (1994 film)</h1>
    <div id="mw-content-text"><div class="mw-parser-output">
      <table class="infobox vevent"><tbody>
        <tr><th class="infobox-label">Directed by</th>
            <td class="infobox-data">Ana Pérez<sup class="reference">[1]</sup></td></tr>
        <tr><th class="infobox-label">Starring</th><td class="infobox-data">
            <div class="plainlist"><ul><li>Actor One</li><li>Actor Two</li></ul></div></td></tr>
        <tr><th class="infobox-label">Running time</th>
            <td class="infobox-data">142 minutes<sup>[2]</sup></td></tr>
        <tr><th class="infobox-label">Countries</th>
            <td class="infobox-data">Mexico<br>Spain</td></tr>
        <tr><th class="infobox-label">Language</th><td class="infobox-data">English</td></tr>
        {infobox_extra}
      </tbody></table>
      {lead}
      <p>Second lead paragraph<sup class="reference">[3]</sup>.</p>
      <div class="mw-heading mw-heading2"><h2 id="Plot">Plot</h2>
        <span class="mw-editsection">[edit]</span></div>
      <p>First plot paragraph.</p>
      <div class="mw-heading mw-heading3"><h3 id="Ending">Ending</h3></div>
      <p>Second plot paragraph.</p>
      <div class="mw-heading mw-heading2"><h2 id="Cast">Cast</h2></div>
      <p>Not part of the plot.</p>
    </div></div>
    <div id="mw-normal-catlinks"><ul>{links}</ul></div>
    </body></html>
    """


def test_parse_film_extracts_metadata():
    page = parse_film(film_html(), FILM_URL)

    assert page is not None
    record = page.record
    assert record.title == "Example"
    assert record.year == 1994
    assert record.directors == "Ana Pérez"
    assert record.cast == "Actor One|Actor Two"
    assert record.countries == "Mexico|Spain"
    assert record.languages == "English"
    assert record.runtime_minutes == 142
    assert record.themes == "friendship"
    assert record.url == FILM_URL


def test_parse_film_combines_category_and_lead_genres():
    page = parse_film(film_html(), FILM_URL)

    assert page.genre_list == ("crime", "drama", "horror")
    assert page.record.genres == "crime|drama|horror"
    assert page.genre_category_urls == (
        "https://en.wikipedia.org/wiki/Category:American_crime_drama_films",
    )


def test_parse_film_separates_summary_from_plot_and_removes_citations():
    record = parse_film(film_html(), FILM_URL).record

    assert record.summary == (
        "Example is a 1994 American horror film. Second lead paragraph."
    )
    assert record.plot == "First plot paragraph. Second plot paragraph."


def test_parse_film_supports_section_wrapped_articles():
    html = """
    <h1 id="firstHeading">Example</h1>
    <div id="mw-content-text"><div class="mw-parser-output">
      <section data-mw-section-id="0">
        <p class="mw-empty-elt"></p>
        <table class="infobox vevent"><tr><th class="infobox-label">Directed by</th>
          <td class="infobox-data">Ana Pérez</td></tr></table>
        <p>Example is a 1994 American horror film.</p>
      </section>
      <section data-mw-section-id="1">
        <div class="mw-heading mw-heading2"><h2 id="Plot">Plot</h2></div>
        <p>First plot paragraph.</p>
        <table><tr><td><p>Table text.</p></td></tr></table>
        <section data-mw-section-id="2">
          <div class="mw-heading mw-heading3"><h3 id="Ending">Ending</h3></div>
          <p>Second plot paragraph.</p>
        </section>
      </section>
      <section data-mw-section-id="3">
        <div class="mw-heading mw-heading2"><h2 id="Cast">Cast</h2></div>
        <p>Not part of the plot.</p>
      </section>
    </div></div>
    <div id="mw-normal-catlinks"><ul>
      <li><a href="/wiki/Category:1994_films">1994 films</a></li>
    </ul></div>
    """

    record = parse_film(html, FILM_URL).record

    assert record.summary == "Example is a 1994 American horror film."
    assert record.plot == "First plot paragraph. Second plot paragraph."
    assert record.genres == "horror"


def test_parse_film_rejects_television_series():
    extra = '<tr><th class="infobox-label">No. of episodes</th><td class="infobox-data">8</td></tr>'

    assert parse_film(film_html(infobox_extra=extra), FILM_URL) is None


def test_parse_film_rejects_film_series():
    lead = "<p>Example is an American horror film series.</p>"

    assert parse_film(film_html(lead=lead), FILM_URL) is None


def test_parse_film_rejects_media_franchise():
    lead = "<p>Example is an American media franchise created by someone.</p>"

    assert parse_film(film_html(lead=lead), FILM_URL) is None


def test_parse_film_accepts_film_that_mentions_its_franchise():
    lead = (
        "<p>Example is a 1994 American horror film. "
        "It launched a media franchise and a film series.</p>"
    )

    assert parse_film(film_html(lead=lead), FILM_URL) is not None


def test_parse_film_accepts_installment_of_a_trilogy():
    lead = "<p>Example is the first film in the Example trilogy, a horror story.</p>"

    assert parse_film(film_html(lead=lead), FILM_URL) is not None


def test_parse_film_rejects_adult_categories():
    categories = [
        ("1994 films", "/wiki/Category:1994_films"),
        ("American pornographic films", "/wiki/Category:American_pornographic_films"),
    ]

    assert parse_film(film_html(cats=categories), FILM_URL) is None


def test_parse_film_rejects_page_without_infobox():
    html = """<h1 id="firstHeading">Drama</h1>
    <div id="mw-content-text"><div class="mw-parser-output"><p>Text.</p></div></div>"""

    assert parse_film(html, FILM_URL) is None


def test_parse_film_rejects_film_without_any_genre():
    categories = [("1994 films", "/wiki/Category:1994_films")]
    lead = "<p>Example is a 1994 American film.</p>"

    assert parse_film(film_html(lead=lead, cats=categories), FILM_URL) is None


def test_genres_from_category_accepts_genre_categories():
    assert genres_from_category("1990s prison drama films") == ["drama"]
    assert genres_from_category("American science fiction action films") == [
        "action",
        "science fiction",
    ]
    assert genres_from_category("Vietnam War films") == ["war"]
    assert genres_from_category("Spaghetti Western films") == ["western"]


def test_genres_from_category_rejects_other_categories():
    rejected = [
        "1994 films",
        "Films about crime",
        "Films set in Western Australia",
        "Saturn Award–winning films",
        "American action short films",
        "American drama television films",
        "Western Australian films",
        "Horror films by decade",
    ]
    assert [name for name in rejected if genres_from_category(name)] == []


def test_normalize_wiki_url_applies_crawling_rules():
    assert normalize_wiki_url("/wiki/Alien_(film)#Plot") == "https://en.wikipedia.org/wiki/Alien_(film)"
    assert normalize_wiki_url("/w/index.php?title=Category:Drama&pagefrom=B") is None
    assert normalize_wiki_url("/wiki/Alien?action=edit") is None
    assert normalize_wiki_url("http://en.wikipedia.org/wiki/Alien") is None
    assert normalize_wiki_url("https://es.wikipedia.org/wiki/Alien") is None
    assert normalize_wiki_url("https://example.com/wiki/Alien") is None


def test_is_article_url_excludes_namespaces_but_allows_colons_in_titles():
    assert is_article_url("https://en.wikipedia.org/wiki/Mad_Max:_Fury_Road")
    assert not is_article_url("https://en.wikipedia.org/wiki/File:Poster.jpg")
    assert not is_article_url("https://en.wikipedia.org/wiki/Category:Drama_films")


def test_parse_category_extracts_articles_and_genre_subcategories():
    html = """
    <div id="mw-subcategories">
      <a href="/wiki/Category:American_horror_comedy_films">American horror comedy films</a>
      <a href="/wiki/Category:Films_about_dogs">Films about dogs</a>
    </div>
    <div id="mw-pages">
      <a href="/w/index.php?title=Category:X&pagefrom=B">next page</a>
      <div class="mw-category">
        <a href="/wiki/Alien_(film)">Alien</a>
        <a href="/wiki/Alien_(film)">Alien</a>
        <a href="/wiki/Template:Foo">Template</a>
      </div>
    </div>
    """

    page = parse_category(html)

    assert page.article_urls == ("https://en.wikipedia.org/wiki/Alien_(film)",)
    assert page.subcategory_urls == (
        "https://en.wikipedia.org/wiki/Category:American_horror_comedy_films",
    )


@pytest.mark.parametrize(
    "title, summary",
    [
        ("Blade (franchise)", "Blade is an American superhero horror film and television franchise."),
        ("The Ace of Spades (serial)", "The Ace of Spades is a 1925 American silent film serial."),
        ("A Chinese Odyssey", "A Chinese Odyssey is Chinese film series directed by Jeffrey Lau."),
        ("Coco Chanel", "Coco Chanel is a 2008 biographical drama television film directed by X."),
        ("Finish Line", "Finish Line is a 1989 American made-for-television sports drama film."),
        ("Ned Blessing", "Ned Blessing is a 1992 made-for-TV movie filmed near Austin."),
        ("Crazy Cruise", "Crazy Cruise is a 1942 American animated comedy short film."),
        ("Bedhead", "Bedhead is a 1991 short family-comedy-fantasy film."),
        ("The Legend", "The Legend is a 2005 Finnish short documentary directed by X."),
    ],
)
def test_is_feature_film_rejects_other_works(title, summary):
    assert not is_feature_film(title, summary, 2000, 90)


@pytest.mark.parametrize(
    "title, summary",
    [
        ("Fantastic Four", "Fantastic Four is a 2015 superhero film based on the film series by X."),
        ("Tekken", "Tekken is a 2009 American martial arts film based on the video game series."),
        ("Weird Woman", "Weird Woman is a 1944 horror film, second in the anthological film series."),
        ("Remake", "Remake is a 1999 American drama film based on the 1985 television film of X."),
        ("Life Is a Miracle", "Life Is a Miracle is a 2004 Serbian romantic comedy film."),
        ("Quick", "Quick is a short-lived 1999 American comedy film."),
    ],
)
def test_is_feature_film_accepts_films_that_mention_other_works(title, summary):
    assert is_feature_film(title, summary, 2000, 90)


def test_is_feature_film_requires_year_and_feature_length():
    summary = "Example is a 1994 American horror film."

    assert not is_feature_film("Example", summary, None, 90)
    assert not is_feature_film("Example", summary, 1994, 39)
    assert is_feature_film("Example", summary, 1994, 40)
    assert is_feature_film("Example", summary, 1994, None)


def test_parse_film_removes_interlanguage_links_from_names():
    html = film_html().replace("Actor One", "Actor One [de]")

    assert parse_film(html, FILM_URL).record.cast == "Actor One|Actor Two"
