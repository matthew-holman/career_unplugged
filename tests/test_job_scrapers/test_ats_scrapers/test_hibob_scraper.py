import pytest

from app.models import CareerPage
from tests.test_job_scrapers.test_ats_scrapers.ats_test_base import run_ats_scraper_test


@pytest.mark.integration
@pytest.mark.network
def test_hibob_scraper() -> None:
    from app.job_scrapers.ats_scrapers.hibob_scraper import HiBobScraper

    career_page = CareerPage(
        company_name="provider trust",
        url="https://providertrust.careers.hibob.com/",
    )

    run_ats_scraper_test(
        scraper_cls=HiBobScraper,
        career_page=career_page,
    )
