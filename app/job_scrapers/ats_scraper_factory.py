from typing import Optional

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.ats_scrapers.teamtailor_scraper import TeamtailorScraper
from app.utils.log_wrapper import LoggerFactory, LogLevels

logger = LoggerFactory.get_logger("AtsParserFactory", log_level=LogLevels.DEBUG)


class AtsScraperFactory:
    SCRAPERS = {TeamtailorScraper}

    @classmethod
    def get_parser(cls, url: str) -> Optional[AtsScraper]:
        for scraper_cls in cls.SCRAPERS:
            if scraper_cls.supports(url):
                logger.debug(f"Matched {scraper_cls.__name__} for {url}")
                return scraper_cls()
        logger.warning(f"No ATS scraper matched for {url}")
        return None
