from typing import List, Optional

from bs4 import BeautifulSoup

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.ats_scrapers.ashby_board_scraper import AshbyBoardScraper
from app.job_scrapers.ats_scrapers.greenhouse_board_scraper import (
    GreenHouseBoardScraper,
)
from app.job_scrapers.ats_scrapers.greenhouse_embedded_scraper import (
    GreenHouseEmbedScraper,
)
from app.job_scrapers.ats_scrapers.lever_scraper import LeverScraper
from app.job_scrapers.ats_scrapers.recruitee_scraper import RecruiteeScraper
from app.job_scrapers.ats_scrapers.teamtailor_scraper import TeamTailorScraper
from app.log import Log
from app.models.career_page import CareerPage


class AtsScraperFactory:
    SCRAPERS: List[type[AtsScraper]] = [
        AshbyBoardScraper,
        GreenHouseBoardScraper,
        GreenHouseEmbedScraper,
        LeverScraper,
        RecruiteeScraper,
        TeamTailorScraper,
    ]

    @classmethod
    def get_ats_scraper(cls, career_page: CareerPage) -> Optional[AtsScraper]:
        response = AtsScraper._fetch_page(career_page.url)
        if not response:
            Log.warning(f"Failed to fetch career page for {career_page.url}")
            return None

        html = response.text or response.content
        soup = BeautifulSoup(html, "html.parser")

        for scraper_cls in cls.SCRAPERS:
            if scraper_cls.supports(soup):
                Log.info(f"Matched {scraper_cls.__name__} for {career_page.url}")
                return scraper_cls(career_page)
        Log.warning(f"No ATS scraper matched for {career_page.url}")
        return None
