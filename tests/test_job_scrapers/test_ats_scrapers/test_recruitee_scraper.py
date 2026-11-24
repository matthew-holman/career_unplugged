from dataclasses import dataclass
from datetime import date

import pytest

from bs4 import BeautifulSoup

from app.job_analysis.description_extractors.recruitee import Recruitee
from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.ats_scrapers.ashby_board_scraper import AshbyBoardScraper
from app.job_scrapers.ats_scrapers.jobylon_scraper import JobylonScraper
from app.job_scrapers.ats_scrapers.recruitee_scraper import (
    RecruiteeJobCard,
    RecruiteeScraper,
)
from app.job_scrapers.ats_scrapers.teamtailor_scraper import TeamTailorScraper
from app.job_scrapers.ats_scrapers.workable_scraper import WorkableScraper
from app.job_scrapers.scraper import JobType, RemoteStatus, Source
from app.models import CareerPage, Job
from tests.test_job_scrapers.test_ats_scrapers.ats_test_base import run_ats_scraper_test

EMPTY_SOUP = BeautifulSoup("", "html.parser")

OFFERS_PAYLOAD: dict[str, object] = {
    "offers": [
        {
            "title": "Senior Backend Engineer",
            "slug": "senior-backend-engineer",
            "careers_url": "https://jobs.acme.com/o/senior-backend-engineer",
            "department": "Engineering",
            "employment_type_code": "fulltime_permanent",
            "published_at": "2026-11-04 09:00:00 UTC",
            "remote": False,
            "hybrid": True,
            "on_site": True,
            "city": "Austin",
            "country": "United States",
            "locations": [
                {"city": "Austin", "country": "United States"},
                {"city": "Berlin", "country": "Deutschland"},
                {"city": "Berlin", "country": "Deutschland"},
            ],
        },
        {
            "title": "Orderpicker",
            "slug": "orderpicker-3",
            "employment_type_code": "parttime_fixed_term",
            "published_at": "not-a-date",
            "remote": False,
            "hybrid": False,
            "on_site": True,
            "city": "Waregem",
            "country": "België",
            "locations": [],
        },
        {
            "title": "Platform Engineer",
            "slug": "platform-engineer",
            "employment_type_code": "freelance",
            "remote": True,
            "hybrid": False,
            "on_site": False,
            "locations": [{"city": None, "country": "Nederland"}],
        },
        {"title": "", "slug": "no-title"},
        {"title": "No slug"},
        "not-a-dict",
    ],
}


def _scraper(url: str = "https://acme.recruitee.com/") -> RecruiteeScraper:
    return RecruiteeScraper(CareerPage(company_name="acme", url=url))


def _cards() -> list[RecruiteeJobCard]:
    return RecruiteeScraper.parse_offers_payload(OFFERS_PAYLOAD)


# --- supports() --------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://acme.recruitee.com/",
        "https://acme.recruitee.com",
        "https://ACME.recruitee.com/o/some-job",
    ],
)
def test_supports_recruitee_urls(url: str) -> None:
    assert RecruiteeScraper.supports(url=url, soup=EMPTY_SOUP)


@pytest.mark.parametrize(
    "url",
    [
        "https://recruitee.com/",
        "https://acme.recruitee.com.evil.io/",
        "https://jobs.acme.com/o/some-job",
        "https://apply.workable.com/acme/",
        "https://acme.teamtailor.com/",
    ],
)
def test_does_not_support_other_urls(url: str) -> None:
    assert not RecruiteeScraper.supports(url=url, soup=EMPTY_SOUP)


def test_other_scrapers_do_not_claim_recruitee() -> None:
    url = "https://acme.recruitee.com/"
    for scraper_cls in (
        WorkableScraper,
        JobylonScraper,
        AshbyBoardScraper,
        TeamTailorScraper,
    ):
        assert not scraper_cls.supports(url=url, soup=EMPTY_SOUP)


# --- payload parsing -----------------------------------------------------------


def test_parse_offers_payload() -> None:
    cards = _cards()

    assert [card.slug for card in cards] == [
        "senior-backend-engineer",
        "orderpicker-3",
        "platform-engineer",
    ]
    # Duplicate locations are merged; top-level city/country is a fallback only.
    assert [loc.city for loc in cards[0].locations] == ["Austin", "Berlin"]
    assert [loc.country for loc in cards[1].locations] == ["België"]


def test_parse_offers_payload_rejects_bad_shapes() -> None:
    assert RecruiteeScraper.parse_offers_payload([]) == []
    assert RecruiteeScraper.parse_offers_payload({"offers": "nope"}) == []


def test_parse_job_card_prefers_european_location() -> None:
    job = _scraper().parse_job_card(_cards()[0])

    assert job is not None
    assert job.title == "Senior Backend Engineer"
    # Board URL format, not the custom-domain careers_url.
    assert job.job_url == "https://acme.recruitee.com/o/senior-backend-engineer"
    assert job.location is not None
    assert job.location.country == "Germany"
    assert job.location.city == "Berlin"
    assert job.date_posted == date(2026, 11, 4)
    assert job.job_type == [JobType.FULL_TIME]
    assert job.remote_status == RemoteStatus.HYBRID
    assert job.source == Source.RECRUITEE
    assert job.company_name == "acme"


def test_parse_job_card_localised_country_and_flags() -> None:
    onsite = _scraper().parse_job_card(_cards()[1])
    assert onsite is not None
    assert onsite.location is not None
    assert onsite.location.country == "Belgium"
    assert onsite.remote_status == RemoteStatus.ONSITE
    assert onsite.job_type == [JobType.PART_TIME]
    assert onsite.date_posted is None

    remote = _scraper().parse_job_card(_cards()[2])
    assert remote is not None
    assert remote.remote_status == RemoteStatus.REMOTE
    assert remote.job_type == [JobType.CONTRACT]


def test_parse_job_card_rejects_non_card() -> None:
    assert _scraper().parse_job_card({"title": "x"}) is None


def test_parse_job_card_requires_board_host() -> None:
    assert _scraper("https://recruitee.com/").parse_job_card(_cards()[0]) is None


# --- fetching ----------------------------------------------------------------


@dataclass(frozen=True)
class _FakeResponse:
    status_code: int
    payload: object = None

    def json(self) -> object:
        return self.payload


def test_find_job_cards_calls_offers_api(monkeypatch: pytest.MonkeyPatch) -> None:
    requested: list[str] = []

    def fake_fetch(url: str, **kwargs: object) -> _FakeResponse:
        requested.append(url)
        return _FakeResponse(200, OFFERS_PAYLOAD)

    monkeypatch.setattr(AtsScraper, "_fetch_page", staticmethod(fake_fetch))

    cards = _scraper("https://acme.recruitee.com/vacatures").find_job_cards(EMPTY_SOUP)

    assert requested == ["https://acme.recruitee.com/api/offers/"]
    assert len(cards) == 3


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


# --- description -------------------------------------------------------------


def test_description_api_url() -> None:
    assert (
        Recruitee.build_api_url("https://acme.recruitee.com/o/senior-engineer")
        == "https://acme.recruitee.com/api/offers/senior-engineer"
    )
    assert Recruitee.build_api_url("https://acme.recruitee.com/") is None
    assert Recruitee.build_api_url("https://jobs.acme.com/o/senior-engineer") is None


def test_description_from_payload() -> None:
    payload = {
        "offer": {
            "description": "<p>About</p>",
            "requirements": "<ul><li>Python</li></ul>",
        }
    }
    assert (
        Recruitee.description_from_payload(payload)
        == "<p>About</p>\n<ul><li>Python</li></ul>"
    )
    assert Recruitee.description_from_payload({"offer": None}) == ""
    assert Recruitee.description_from_payload(None) == ""


def test_description_prefers_api(monkeypatch: pytest.MonkeyPatch) -> None:
    requested: list[str] = []

    def fake_fetch(url: str, **kwargs: object) -> _FakeResponse:
        requested.append(url)
        return _FakeResponse(200, {"offer": {"description": "<p>From API</p>"}})

    monkeypatch.setattr(AtsScraper, "_fetch_page", staticmethod(fake_fetch))
    job = Job(
        title="Engineer",
        company="acme",
        source=Source.RECRUITEE,
        ats_source_url="https://acme.recruitee.com/o/engineer",
    )
    page = BeautifulSoup("<h2>Job description</h2><p>From page</p>", "html.parser")

    assert Recruitee.extract_description(page, job) == "<p>From API</p>"
    assert requested == ["https://acme.recruitee.com/api/offers/engineer"]


def test_description_falls_back_to_page(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        AtsScraper, "_fetch_page", staticmethod(lambda url, **kwargs: None)
    )
    job = Job(
        title="Engineer",
        company="acme",
        source=Source.RECRUITEE,
        ats_source_url="https://acme.recruitee.com/o/engineer",
    )
    page = BeautifulSoup(
        "<div><h2>Job description</h2><p>From page</p></div>", "html.parser"
    )

    assert Recruitee.extract_description(page, job) == "<p>From page</p>"


@pytest.mark.integration
@pytest.mark.network
def test_recruitee_scraper() -> None:
    career_page = CareerPage(
        company_name="befood",
        url="https://befood.recruitee.com/",
    )

    run_ats_scraper_test(
        scraper_cls=RecruiteeScraper,
        career_page=career_page,
    )
