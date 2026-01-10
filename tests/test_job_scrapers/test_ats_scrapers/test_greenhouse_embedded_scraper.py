import pytest

from app.models import CareerPage
from tests.test_job_scrapers.test_ats_scrapers.ats_test_base import run_ats_scraper_test


@pytest.mark.integration
@pytest.mark.network
def test_greenhouse_board_scraper_wordpress() -> None:
    from app.job_scrapers.ats_scrapers.greenhouse_embedded_scraper import (
        GreenHouseEmbedScraper,
    )

    career_page = CareerPage(
        company_name="cast ai",
        url="https://cast.ai/careers/",
    )

    run_ats_scraper_test(
        scraper_cls=GreenHouseEmbedScraper,
        career_page=career_page,
    )


@pytest.mark.integration
@pytest.mark.network
def test_greenhouse_board_scraper_official() -> None:
    from app.job_scrapers.ats_scrapers.greenhouse_embedded_scraper import (
        GreenHouseEmbedScraper,
    )

    career_page = CareerPage(
        company_name="addepar",
        url="https://addepar.com/careers",
    )

    run_ats_scraper_test(
        scraper_cls=GreenHouseEmbedScraper,
        career_page=career_page,
    )
