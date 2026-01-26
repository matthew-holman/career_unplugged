from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.ats_scraper_factory import AtsScraperFactory
from app.job_scrapers.ats_scrapers.ashby_board_scraper import AshbyBoardScraper
from app.job_scrapers.ats_scrapers.lever_scraper import LeverScraper
from app.models import CareerPage


class _FakeResponse(tuple):
    __slots__ = ()
    _fields = ("text",)

    def __new__(cls, text: str):  # type: ignore[override]
        return tuple.__new__(cls, (text,))

    @property
    def text(self) -> str:
        return self[0]


def test_get_ats_scraper_ashby(monkeypatch):
    html = (
        "<html><script>"
        'window.__appData = {"jobBoard": {"jobPostings": []}};'
        "</script></html>"
    )

    monkeypatch.setattr(AtsScraper, "_fetch_page", lambda url: _FakeResponse(html))

    career_page = CareerPage(
        company_name="aspora",
        url="https://jobs.ashbyhq.com/aspora",
    )

    ats_scraper = AtsScraperFactory.get_ats_scraper(career_page)

    assert isinstance(ats_scraper, AshbyBoardScraper)


def test_get_ats_scraper_lever(monkeypatch):
    html = "<meta property='og:url' content='https://jobs.eu.lever.co/tomtom'>"
    monkeypatch.setattr(AtsScraper, "_fetch_page", lambda url: _FakeResponse(html))

    career_page = CareerPage(
        company_name="acme",
        url="https://jobs.lever.co/acme",
    )

    ats_scraper = AtsScraperFactory.get_ats_scraper(career_page)

    assert isinstance(ats_scraper, LeverScraper)
