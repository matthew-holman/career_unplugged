from app.job_scrapers.ats_scraper_factory import AtsScraperFactory
from app.job_scrapers.ats_scrapers.ashby_board_scraper import AshbyBoardScraper
from app.job_scrapers.ats_scrapers.lever_scraper import LeverScraper
from app.models import CareerPage


def test_get_ats_scraper():
    career_page = CareerPage(
        company_name="aspora",
        url="https://jobs.ashbyhq.com/aspora",
    )

    ats_scraper = AtsScraperFactory.get_ats_scraper(career_page)

    assert isinstance(ats_scraper, AshbyBoardScraper)


def test_get_ats_scraper_lever():
    career_page = CareerPage(
        company_name="acme",
        url="https://jobs.lever.co/acme",
    )

    ats_scraper = AtsScraperFactory.get_ats_scraper(career_page)

    assert isinstance(ats_scraper, LeverScraper)
