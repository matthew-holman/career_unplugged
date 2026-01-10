from typing import List, Optional

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.ats_scrapers.ashby_board_scraper import AshbyBoardScraper
from app.job_scrapers.ats_scrapers.greenhouse_board_scraper import (
    GreenHouseBoardScraper,
)
from app.job_scrapers.ats_scrapers.greenhouse_embedded_scraper import (
    GreenHouseEmbedScraper,
)
from app.job_scrapers.ats_scrapers.lever_scraper import LeverScraper
from app.job_scrapers.ats_scrapers.teamtailor_scraper import TeamTailorScraper
from app.log import Log
from app.models.career_page import CareerPage


class AtsScraperFactory:
    SCRAPERS: List[type[AtsScraper]] = [
        AshbyBoardScraper,
        GreenHouseBoardScraper,
        GreenHouseEmbedScraper,
        LeverScraper,
        TeamTailorScraper,
    ]

    @classmethod
    def get_ats_scraper(cls, career_page: CareerPage) -> Optional[AtsScraper]:
        for scraper_cls in cls.SCRAPERS:
            if scraper_cls.supports(career_page.url):
                Log.info(f"Matched {scraper_cls.__name__} for {career_page.url}")
                return scraper_cls(career_page)
        Log.warning(f"No ATS scraper matched for {career_page.url}")
        return None
