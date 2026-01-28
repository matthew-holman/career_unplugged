from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import RemoteStatus


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


def test_hint_ignored_when_not_location_like() -> None:
    location, remote_status = AtsScraper.extract_location_and_remote_status(
        card_text="Berlin, Germany - On-site", location_hint="Head Office"
    )

    assert location is not None
    assert location.city == "Berlin"
    assert location.country == "Germany"
    assert remote_status == RemoteStatus.ONSITE
