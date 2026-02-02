from app.job_scrapers.scraper import Source
from app.utils.ats_discovery import discover_career_page


def test_normalize_teamtailor_urls() -> None:
    result = discover_career_page("https://acme.teamtailor.com/jobs/123")
    assert result is not None
    assert result.url == "https://acme.teamtailor.com/"
    assert result.source == Source.TEAMTAILOR
    result = discover_career_page("https://acme.teamtailor.com/")
    assert result is not None
    assert result.url == "https://acme.teamtailor.com/"


def test_normalize_greenhouse_urls() -> None:
    result = discover_career_page("https://job-boards.greenhouse.io/acme/jobs/123")
    assert result is not None
    assert result.url == "https://job-boards.greenhouse.io/acme"
    assert result.source == Source.GREENHOUSE_BOARD
    result = discover_career_page("https://job-boards.eu.greenhouse.io/acme/jobs/123")
    assert result is not None
    assert result.url == "https://job-boards.eu.greenhouse.io/acme"


def test_normalize_ashby_urls() -> None:
    result = discover_career_page("https://jobs.ashbyhq.com/acme/123")
    assert result is not None
    assert result.url == "https://jobs.ashbyhq.com/acme"
    assert result.source == Source.ASHBY
    result = discover_career_page("https://jobs.ashbyhq.com/acme")
    assert result is not None
    assert result.url == "https://jobs.ashbyhq.com/acme"


def test_normalize_unknown_or_missing_slug() -> None:
    assert discover_career_page("https://example.com/jobs/123") is None
    assert discover_career_page("https://job-boards.greenhouse.io/") is None
