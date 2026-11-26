import pytest

from app.job_scrapers.scraper import Source
from app.utils.ats_discovery import (
    discover_career_page,
    discover_custom_career_page,
    extract_slug_from_career_page_url,
)


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


def test_normalize_workable_urls() -> None:
    result = discover_career_page("https://apply.workable.com/acme/j/ABC123/")
    assert result is not None
    assert result.url == "https://apply.workable.com/acme"
    assert result.source == Source.WORKABLE


def test_workable_shortlink_has_no_slug() -> None:
    assert discover_career_page("https://apply.workable.com/j/ABC123") is None


def test_normalize_jobylon_subdomain_board() -> None:
    result = discover_career_page("https://lindab.jobylon.com/jobs/123-lindab-x/")
    assert result is not None
    assert result.url == "https://lindab.jobylon.com"
    assert result.source == Source.JOBYLON
    assert extract_slug_from_career_page_url(result.url) == "lindab"


def test_bamboohr_board_has_bamboo_source() -> None:
    result = discover_career_page("https://acme.bamboohr.com/careers/42")
    assert result is not None
    assert result.url == "https://acme.bamboohr.com"
    assert result.source == Source.BAMBOO


@pytest.mark.parametrize(
    "url",
    [
        # LinkedIn apply links: the job page does not name the company board.
        "https://emp.jobylon.com/jobs/312345-acme-backend-engineer/",
        "https://cdn.jobylon.com/jobs/companies/123/embed/v5/",
        "https://www.jobylon.com/careers",
        "https://jobylon.com/",
    ],
)
def test_jobylon_own_hosts_are_not_boards(url: str) -> None:
    assert discover_career_page(url) is None
    assert extract_slug_from_career_page_url(url) is None


@pytest.mark.parametrize(
    ("apply_url", "expected"),
    [
        ("https://careers.acme.com/jobs/123-engineer", "https://careers.acme.com"),
        ("https://jobs.acme.co.uk/?ref=linkedin", "https://jobs.acme.co.uk"),
        ("https://www.acme.com/careers/123?utm=x", "https://www.acme.com/careers"),
        ("https://acme.com/en/Careers/123", "https://acme.com/en/Careers"),
        ("https://acme.se/lediga-jobb/456", "https://acme.se/lediga-jobb"),
    ],
)
def test_discover_custom_career_page(apply_url: str, expected: str) -> None:
    assert discover_custom_career_page(apply_url) == expected


@pytest.mark.parametrize(
    "apply_url",
    [
        # Shared ATS and job board hosts name the vendor, not the company.
        "https://acme.wd3.myworkdayjobs.com/careers/job/123",
        "https://jobs.smartrecruiters.com/Acme/123",
        "https://boards.greenhouse.io/acme/jobs/123",
        "https://careers-acme.icims.com/jobs/123",
        "https://www.linkedin.com/jobs/view/123",
        # Nothing careers-like in the host or near the top of the path.
        "https://acme.com/apply?id=123",
        "https://acme.com/a/b/careers/123",
        "https://jobs.com/123",
        "mailto:jobs@acme.com",
        "not a url",
    ],
)
def test_discover_custom_career_page_rejects(apply_url: str) -> None:
    assert discover_custom_career_page(apply_url) is None
