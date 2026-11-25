import pytest

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import RemoteStatus
from app.utils.locations.location_parser import LocationParser


def test_location_hint_with_hybrid() -> None:
    location, remote_status = AtsScraper.extract_location_and_remote_status(
        card_text="Software Engineer - Hybrid", location_hint="Berlin, Germany"
    )

    assert location is not None
    assert location.city == "Berlin"
    assert location.country == "Germany"
    assert remote_status == RemoteStatus.HYBRID


def test_ambiguous_remote_markers() -> None:
    location, remote_status = AtsScraper.extract_location_and_remote_status(
        card_text="On-site, Remote, Hybrid", location_hint=None
    )

    assert location is None
    assert remote_status == RemoteStatus.UNKNOWN


@pytest.mark.parametrize(
    "raw, expected_city, expected_country",
    [
        ("Göteborg, Sweden", "Gothenburg", "Sweden"),
        ("Göteborg", "Gothenburg", "Sweden"),
        ("København", "Copenhagen", "Denmark"),
        ("København, Denmark", "Copenhagen", "Denmark"),
        ("München, Germany", "Munich", "Germany"),
        ("münchen", "Munich", "Germany"),
        ("Wien, Austria", "Vienna", "Austria"),
        ("Praha, Czech Republic", "Prague", "Czech Republic"),
        ("Berlin, Germany", "Berlin", "Germany"),  # no alias — unchanged
    ],
)
def test_city_aliases(raw: str, expected_city: str, expected_country: str) -> None:
    city, country = LocationParser.parse_location(raw)
    assert city == expected_city
    assert country == expected_country


def test_hint_ignored_when_not_location_like() -> None:
    location, remote_status = AtsScraper.extract_location_and_remote_status(
        card_text="Berlin, Germany - On-site", location_hint="Head Office"
    )

    assert location is not None
    assert location.city == "Berlin"
    assert location.country == "Germany"
    assert remote_status == RemoteStatus.ONSITE


@pytest.mark.parametrize(
    "hint, expected_city, expected_country",
    [
        # Hyphenated names are not split into "Baden - Württemberg".
        ("Karlsruhe, Baden-Württemberg", "Karlsruhe", "Germany"),
        ("Stoke-on-Trent, Staffordshire", "Stoke-on-Trent", "United Kingdom"),
        # Regions and localised country names resolve to a country, not a city.
        ("Speyer, Rheinland-Pfalz", "Speyer", "Germany"),
        ("Graz, Österreich", "Graz", "Austria"),
        ("Zwolle, Overijssel", "Zwolle", "Netherlands"),
        ("Bukarest, Rumänien", "Bukarest", "Romania"),
        ("Northern Ireland", None, "United Kingdom"),
        ("Czechia", None, "Czech Republic"),
        # "Country, City"
        ("Cyprus, Ypsonas", "Ypsonas", "Cyprus"),
        # Spaced dashes separate parts.
        ("The Hague - hybrid", "The Hague", "Netherlands"),
        ("Germany - Krumbach | Hybrid", "Krumbach", "Germany"),
        # Location parentheticals are kept, others dropped.
        ("Remote (Europe)", None, "Europe"),
        ("Dorchester (GB)", "Dorchester", "United Kingdom"),
        ("Köln (DE) / Bonn (DE)", "Cologne", "Germany"),
        # Token matching keeps accented letters.
        ("Kirchheim bei München", "Kirchheim bei München", "Germany"),
        # ';'-separated country lists.
        ("Austria; Germany", None, "Austria"),
        ("Germany (Remote); Poland (Remote)", None, "Germany"),
    ],
)
def test_european_location_hints(
    hint: str, expected_city: str | None, expected_country: str
) -> None:
    location, _ = AtsScraper.extract_location_and_remote_status(
        card_text="Engineer", location_hint=hint
    )

    assert location is not None
    assert location.city == expected_city
    assert location.country == expected_country


@pytest.mark.parametrize(
    "hint, wrong_country",
    [
        # English county names that are also North American places.
        ("Surrey, British Columbia", "United Kingdom"),
        ("Norfolk VA", "United Kingdom"),
        ("Kent, WA", "United Kingdom"),
        # Spanish towns sharing a name with Latin American cities are not added.
        ("Granada, Nicaragua", "Spain"),
    ],
)
def test_ambiguous_place_names_do_not_resolve_to_europe(
    hint: str, wrong_country: str
) -> None:
    location, _ = AtsScraper.extract_location_and_remote_status(
        card_text="Engineer", location_hint=hint
    )

    assert location is None or location.country != wrong_country
