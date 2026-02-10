import pytest

from app.job_scrapers.ats_scrapers.bamboohr_scraper import BambooHrScraper
from app.models import CareerPage
from tests.test_job_scrapers.test_ats_scrapers.ats_test_base import run_ats_scraper_test


@pytest.mark.integration
@pytest.mark.network
def test_greenhouse_board_scraper() -> None:

    career_page = CareerPage(
        company_name="cronoslabs",
        url="https://cronoslabs.bamboohr.com",
    )

    run_ats_scraper_test(
        scraper_cls=BambooHrScraper,
        career_page=career_page,
    )
