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
