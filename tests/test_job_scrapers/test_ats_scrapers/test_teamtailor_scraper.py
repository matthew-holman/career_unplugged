import pytest

from app.models import CareerPage
from tests.test_job_scrapers.test_ats_scrapers.ats_test_base import run_ats_scraper_test


@pytest.mark.integration
@pytest.mark.network
def test_teamtailor_scraper() -> None:
    from app.job_scrapers.ats_scrapers.teamtailor_scraper import (
        TeamTailorScraper,
    )

    career_page = CareerPage(
        company_name="na-kd",
        url="https://career.na-kd.com/",
    )

    run_ats_scraper_test(
        scraper_cls=TeamTailorScraper,
        career_page=career_page,
    )
