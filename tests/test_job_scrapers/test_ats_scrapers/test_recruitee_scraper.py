import pytest

from app.models import CareerPage
from tests.test_job_scrapers.test_ats_scrapers.ats_test_base import run_ats_scraper_test


@pytest.mark.integration
@pytest.mark.network
def test_recruitee_scraper() -> None:
    from app.job_scrapers.ats_scrapers.recruitee_scraper import RecruiteeScraper

    career_page = CareerPage(
        company_name="hostaway",
        url="https://careers.hostaway.com/",
    )

    run_ats_scraper_test(
        scraper_cls=RecruiteeScraper,
        career_page=career_page,
    )
