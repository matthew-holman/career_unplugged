import pytest

from app.models import CareerPage
from tests.test_job_scrapers.test_ats_scrapers.ats_test_base import run_ats_scraper_test


def test_lever_supports_positive() -> None:
    from bs4 import BeautifulSoup

    from app.job_scrapers.ats_scrapers.lever_scraper import LeverScraper

    html = '<div class="lever-jobs-container"></div>'
    soup = BeautifulSoup(html, "html.parser")

    assert LeverScraper.supports(url="https://example.com", soup=soup) is True


def test_lever_supports_negative() -> None:
    from bs4 import BeautifulSoup

    from app.job_scrapers.ats_scrapers.lever_scraper import LeverScraper

    soup = BeautifulSoup("<html></html>", "html.parser")

    assert LeverScraper.supports(url="https://example.com", soup=soup) is False


@pytest.mark.integration
@pytest.mark.network
def test_lever_scraper() -> None:
    from app.job_scrapers.ats_scrapers.lever_scraper import LeverScraper

    career_page = CareerPage(
        company_name="tomtom",
        url="https://jobs.eu.lever.co/tomtom",
        active=True,
    )

    run_ats_scraper_test(
        scraper_cls=LeverScraper,
        career_page=career_page,
    )
