import pytest

from app.models import CareerPage
from tests.test_job_scrapers.test_ats_scrapers.ats_test_base import run_ats_scraper_test


@pytest.mark.integration
@pytest.mark.network
def test_greenhouse_board_scraper() -> None:
    from app.job_scrapers.ats_scrapers.ashby_board_scraper import (
        AshbyBoardScraper,
    )

    career_page = CareerPage(
        company_name="roompricegenie",
        url="https://jobs.ashbyhq.com/roompricegenie/",
    )

    run_ats_scraper_test(
        scraper_cls=AshbyBoardScraper,
        career_page=career_page,
    )
