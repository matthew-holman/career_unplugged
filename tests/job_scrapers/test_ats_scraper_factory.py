from app.job_scrapers.ats_scraper_factory import AtsScraperFactory
from app.job_scrapers.ats_scrapers.ashby_board_scraper import AshbyBoardScraper
from app.models import CareerPage


def test_get_ats_scraper():
    career_page = CareerPage(
        company_name="aspora",
        url="https://jobs.ashbyhq.com/aspora",
    )

    ats_scraper = AtsScraperFactory.get_ats_scraper(career_page)

    assert isinstance(ats_scraper, AshbyBoardScraper)
