from datetime import date

import pytest

from bs4 import BeautifulSoup

from app.job_analysis.description_extractors.workable import Workable
from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.ats_scrapers.ashby_board_scraper import AshbyBoardScraper
from app.job_scrapers.ats_scrapers.lever_scraper import LeverScraper
from app.job_scrapers.ats_scrapers.teamtailor_scraper import TeamTailorScraper
from app.job_scrapers.ats_scrapers.workable_scraper import (
    WorkableJobCard,
    WorkableScraper,
)
from app.job_scrapers.scraper import JobType, RemoteStatus, Source
from app.models import CareerPage
from tests.test_job_scrapers.test_ats_scrapers.ats_test_base import run_ats_scraper_test

EMPTY_SOUP = BeautifulSoup("", "html.parser")

WIDGET_PAYLOAD: dict[str, object] = {
    "name": "Acme",
    "jobs": [
        {
            "title": "Senior Backend Engineer",
            "shortcode": "ABC123",
            "employment_type": "Full-time",
            "telecommuting": False,
            "department": "Engineering",
            "published_on": "2026-11-04",
            "country": "United States",
            "city": "New York",
            "locations": [
                {
                    "country": "United States",
                    "countryCode": "US",
                    "city": "New York",
                    "region": "New York",
                    "hidden": False,
                }
            ],
        },
        {
            "title": "Senior Backend Engineer",
            "shortcode": "ABC123",
            "employment_type": "Full-time",
            "telecommuting": False,
            "department": "Engineering",
            "published_on": "2026-11-04",
            "country": "Sweden",
            "city": "Stockholm",
            "locations": [
                {
                    "country": "Sweden",
                    "countryCode": "SE",
                    "city": "Stockholm",
                    "region": "Stockholm County",
                    "hidden": False,
                }
            ],
        },
        {
            "title": "Platform Engineer",
            "shortcode": "DEF456",
            "employment_type": "Contract",
            "telecommuting": True,
            "department": "Engineering",
            "published_on": "2026-10-01",
            "country": "Germany",
            "city": "",
            "locations": [{"country": "Germany", "countryCode": "DE", "hidden": False}],
        },
        {"title": "", "shortcode": "NOTITLE"},
        {"title": "No shortcode"},
        "not-a-dict",
    ],
}


def _scraper(url: str = "https://apply.workable.com/acme/") -> WorkableScraper:
    return WorkableScraper(CareerPage(company_name="acme", url=url))


@pytest.mark.parametrize(
    "url",
    [
        "https://apply.workable.com/acme/",
        "https://apply.workable.com/acme",
        "https://APPLY.workable.com/acme/j/ABC123/",
    ],
)
def test_supports_workable_urls(url: str) -> None:
    assert WorkableScraper.supports(url=url, soup=EMPTY_SOUP)


@pytest.mark.parametrize(
    "url",
    [
        "https://apply.workable.com/",
        "https://apply.workable.com/j/ABC123",
        "https://acme.workable.com/",
        "https://jobs.ashbyhq.com/acme",
        "https://acme.teamtailor.com/",
        "https://jobs.lever.co/acme",
    ],
)
def test_does_not_support_other_urls(url: str) -> None:
    assert not WorkableScraper.supports(url=url, soup=EMPTY_SOUP)


def test_other_scrapers_do_not_claim_workable() -> None:
    url = "https://apply.workable.com/acme/"
    for scraper_cls in (AshbyBoardScraper, TeamTailorScraper, LeverScraper):
        assert not scraper_cls.supports(url=url, soup=EMPTY_SOUP)


def test_parse_widget_payload_merges_locations_by_shortcode() -> None:
    cards = WorkableScraper.parse_widget_payload(WIDGET_PAYLOAD)

    assert [card.shortcode for card in cards] == ["ABC123", "DEF456"]
    assert [loc.country for loc in cards[0].locations] == [
        "United States",
        "Sweden",
    ]


def test_parse_widget_payload_rejects_bad_shapes() -> None:
    assert WorkableScraper.parse_widget_payload([]) == []
    assert WorkableScraper.parse_widget_payload({"jobs": "nope"}) == []


def test_parse_job_card_prefers_european_location() -> None:
    cards = WorkableScraper.parse_widget_payload(WIDGET_PAYLOAD)
    job = _scraper().parse_job_card(cards[0])

    assert job is not None
    assert job.title == "Senior Backend Engineer"
    assert job.job_url == "https://apply.workable.com/acme/j/ABC123/"
    assert job.location is not None
    assert job.location.country == "Sweden"
    assert job.location.city == "Stockholm"
    assert job.date_posted == date(2026, 11, 4)
    assert job.job_type == [JobType.FULL_TIME]
    assert job.source == Source.WORKABLE
    assert job.company_name == "acme"


def test_parse_job_card_telecommuting_is_remote() -> None:
    cards = WorkableScraper.parse_widget_payload(WIDGET_PAYLOAD)
    job = _scraper().parse_job_card(cards[1])

    assert job is not None
    assert job.remote_status == RemoteStatus.REMOTE
    assert job.job_type == [JobType.CONTRACT]
    assert job.location is not None
    assert job.location.country == "Germany"


def test_parse_job_card_rejects_non_card() -> None:
    assert _scraper().parse_job_card({"title": "x"}) is None


def test_parse_job_card_requires_slug() -> None:
    card = WorkableJobCard(
        title="Engineer",
        shortcode="X1",
        department=None,
        employment_type=None,
        telecommuting=False,
        published_on=None,
        locations=(),
    )
    assert _scraper("https://apply.workable.com/").parse_job_card(card) is None


class _FakeResponse:
    def __init__(self, status_code: int, payload: object = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        return self._payload


@pytest.mark.parametrize("status_code", [404, 429, 500])
def test_find_job_cards_handles_error_status(
    monkeypatch: pytest.MonkeyPatch, status_code: int
) -> None:
    monkeypatch.setattr(
        AtsScraper,
        "_fetch_page",
        staticmethod(lambda url, **kwargs: _FakeResponse(status_code)),
    )
    assert _scraper().find_job_cards(EMPTY_SOUP) == []


def test_find_job_cards_calls_widget_api(monkeypatch: pytest.MonkeyPatch) -> None:
    requested: list[str] = []

    def fake_fetch(url: str, **kwargs: object) -> _FakeResponse:
        requested.append(url)
        return _FakeResponse(200, WIDGET_PAYLOAD)

    monkeypatch.setattr(AtsScraper, "_fetch_page", staticmethod(fake_fetch))

    cards = _scraper().find_job_cards(EMPTY_SOUP)

    assert requested == ["https://apply.workable.com/api/v1/widget/accounts/acme"]
    assert len(cards) == 2


def test_description_api_url() -> None:
    assert (
        Workable.build_api_url("https://apply.workable.com/acme/j/ABC123/")
        == "https://apply.workable.com/api/v2/accounts/acme/jobs/ABC123"
    )
    assert Workable.build_api_url("https://apply.workable.com/j/ABC123") is None
    assert Workable.build_api_url("https://apply.workable.com/acme/") is None
    assert Workable.build_api_url("https://jobs.lever.co/acme/j/ABC123") is None


def test_description_from_payload() -> None:
    payload = {
        "description": "<p>About</p>",
        "requirements": "<ul><li>Python</li></ul>",
        "benefits": "",
    }
    assert (
        Workable.description_from_payload(payload)
        == "<p>About</p>\n<ul><li>Python</li></ul>"
    )
    assert Workable.description_from_payload(None) == ""


@pytest.mark.integration
@pytest.mark.network
def test_workable_scraper() -> None:
    career_page = CareerPage(
        company_name="runware",
        url="https://apply.workable.com/runware/",
    )

    run_ats_scraper_test(
        scraper_cls=WorkableScraper,
        career_page=career_page,
    )
