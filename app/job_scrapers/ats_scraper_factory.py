from typing import Optional

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.ats_scrapers.greenhouse_scraper import GreenHouseScraper
from app.job_scrapers.ats_scrapers.teamtailor_scraper import TeamTailorScraper
from app.models.career_page import CareerPage
from app.utils.log_wrapper import LoggerFactory, LogLevels

logger = LoggerFactory.get_logger("AtsParserFactory", log_level=LogLevels.DEBUG)


class AtsScraperFactory:
    SCRAPERS = {TeamTailorScraper, GreenHouseScraper}

    @classmethod
    def get_parser(cls, career_page: CareerPage) -> Optional[AtsScraper]:
        for scraper_cls in cls.SCRAPERS:
            if scraper_cls.supports(career_page.url):
                logger.debug(f"Matched {scraper_cls.__name__} for {career_page.url}")
                return scraper_cls(career_page)
        logger.warning(f"No ATS scraper matched for {career_page.url}")
        return None
