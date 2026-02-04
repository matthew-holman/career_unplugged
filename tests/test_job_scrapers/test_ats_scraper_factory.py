import pytest

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.ats_scraper_factory import (
    AtsScraperFactory,
    CareerPageDeactivatedError,
)
from app.job_scrapers.ats_scrapers.ashby_board_scraper import AshbyBoardScraper
from app.job_scrapers.ats_scrapers.hibob_scraper import HiBobScraper
from app.job_scrapers.ats_scrapers.lever_scraper import LeverScraper
from app.models import CareerPage


class _FakeResponse:
    __slots__ = ("text", "content", "status_code", "history", "url")

    def __init__(
        self,
        text: str,
        status_code: int = 200,
        history: tuple[object, ...] = (),
        url: str = "",
    ) -> None:
        self.text = text
        self.content = text.encode("utf-8")
        self.status_code = status_code
        self.history = history
        self.url = url


def test_get_ats_scraper_ashby(monkeypatch):
    html = (
        "<html><script>"
        'window.__appData = {"jobBoard": {"jobPostings": []}};'
        "</script></html>"
    )

    monkeypatch.setattr(
        AtsScraper, "_fetch_page", lambda url, **kwargs: _FakeResponse(html)
    )

    career_page = CareerPage(
        company_name="aspora",
        url="https://jobs.ashbyhq.com/aspora",
    )

    ats_scraper = AtsScraperFactory.get_ats_scraper(career_page)

    assert isinstance(ats_scraper, AshbyBoardScraper)


def test_get_ats_scraper_lever(monkeypatch):
    html = "<meta property='og:url' content='https://jobs.eu.lever.co/tomtom'>"
    monkeypatch.setattr(
        AtsScraper, "_fetch_page", lambda url, **kwargs: _FakeResponse(html)
    )

    career_page = CareerPage(
        company_name="acme",
        url="https://jobs.lever.co/acme",
    )

    ats_scraper = AtsScraperFactory.get_ats_scraper(career_page)

    assert isinstance(ats_scraper, LeverScraper)


def test_get_ats_scraper_hibob(monkeypatch):
    html = "<meta property='og:url' content='https://wiredscore.careers.hibob.com/'>"
    monkeypatch.setattr(
        AtsScraper, "_fetch_page", lambda url, **kwargs: _FakeResponse(html)
    )

    career_page = CareerPage(
        company_name="wiredscore",
        url="https://wiredscore.careers.hibob.com/",
    )

    ats_scraper = AtsScraperFactory.get_ats_scraper(career_page)

    assert isinstance(ats_scraper, HiBobScraper)


def test_get_ats_scraper_deactivates_on_404(monkeypatch):
    monkeypatch.setattr(
        AtsScraper,
        "_fetch_page",
        lambda url, **kwargs: _FakeResponse("", status_code=404),
    )
    career_page = CareerPage(company_name="acme", url="https://example.com/jobs")

    with pytest.raises(CareerPageDeactivatedError) as exc:
        AtsScraperFactory.get_ats_scraper(career_page)

    assert exc.value.status_code == 404


def test_get_ats_scraper_deactivates_on_403(monkeypatch):
    monkeypatch.setattr(
        AtsScraper,
        "_fetch_page",
        lambda url, **kwargs: _FakeResponse("", status_code=403),
    )
    career_page = CareerPage(company_name="acme", url="https://example.com/jobs")

    with pytest.raises(CareerPageDeactivatedError) as exc:
        AtsScraperFactory.get_ats_scraper(career_page)

    assert exc.value.status_code == 403


def test_get_ats_scraper_deactivates_on_301(monkeypatch):
    redirect = _FakeResponse("", status_code=301)
    monkeypatch.setattr(
        AtsScraper,
        "_fetch_page",
        lambda url, **kwargs: _FakeResponse(
            "", status_code=200, history=(redirect,), url="https://recruitee.com/"
        ),
    )
    career_page = CareerPage(company_name="acme", url="https://example.com/jobs")

    with pytest.raises(CareerPageDeactivatedError) as exc:
        AtsScraperFactory.get_ats_scraper(career_page)

    assert exc.value.status_code == 301


def test_get_ats_scraper_ignores_301_to_customer_domain(monkeypatch, caplog):
    redirect = _FakeResponse("", status_code=301)
    html = '<div class="lever.co"></div>'
    monkeypatch.setattr(
        AtsScraper,
        "_fetch_page",
        lambda url, **kwargs: _FakeResponse(
            html,
            status_code=200,
            history=(redirect,),
            url="https://careers.example.com/jobs",
        ),
    )
    career_page = CareerPage(company_name="acme", url="https://example.com/jobs")

    ats_scraper = AtsScraperFactory.get_ats_scraper(career_page)

    assert isinstance(ats_scraper, LeverScraper)
    assert any("not deactivating" in record.message for record in caplog.records)


def test_get_ats_scraper_does_not_deactivate_on_none_response(monkeypatch):
    monkeypatch.setattr(AtsScraper, "_fetch_page", lambda url, **kwargs: None)
    career_page = CareerPage(company_name="acme", url="https://example.com/jobs")

    ats_scraper = AtsScraperFactory.get_ats_scraper(career_page)

    assert ats_scraper is None
    assert career_page.active is True
    assert career_page.deactivated_at is None
    assert career_page.last_status_code is None
