from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.ats_scrapers.ashby_board_scraper import AshbyBoardScraper
from app.job_scrapers.ats_scrapers.greenhouse_board_scraper import (
    GreenHouseBoardScraper,
)
from app.job_scrapers.ats_scrapers.greenhouse_embedded_scraper import (
    GreenHouseEmbedScraper,
)
from app.job_scrapers.ats_scrapers.hibob_scraper import HiBobScraper
from app.job_scrapers.ats_scrapers.lever_scraper import LeverScraper
from app.job_scrapers.ats_scrapers.personio_scraper import PersonioScraper
from app.job_scrapers.ats_scrapers.recruitee_scraper import RecruiteeScraper
from app.job_scrapers.ats_scrapers.teamtailor_scraper import TeamTailorScraper
from app.log import Log
from app.models.career_page import CareerPage


@dataclass(frozen=True)
class CareerPageDeactivatedError(Exception):
    status_code: int


_DEACTIVATE_REDIRECT_HOST_SUFFIXES = ("recruitee.com",)


class AtsScraperFactory:
    SCRAPERS: List[type[AtsScraper]] = [
        AshbyBoardScraper,
        GreenHouseBoardScraper,
        GreenHouseEmbedScraper,
        HiBobScraper,
        LeverScraper,
        PersonioScraper,
        RecruiteeScraper,
        TeamTailorScraper,
    ]

    @classmethod
    def get_ats_scraper(cls, career_page: CareerPage) -> Optional[AtsScraper]:
        if not career_page.active:
            return None

        response = AtsScraper._fetch_page(career_page.url, return_non_200=True)
        if response is None:
            Log.warning(f"Failed to fetch career page for {career_page.url}")
            return None

        status_code = cls._deactivation_status(response, career_page)
        if status_code is not None:
            raise CareerPageDeactivatedError(status_code=status_code)

        html = response.text or response.content
        soup = BeautifulSoup(html, "html.parser")

        for scraper_cls in cls.SCRAPERS:
            if scraper_cls.supports(url=career_page.url, soup=soup):
                Log.info(f"Matched {scraper_cls.__name__} for {career_page.url}")
                return scraper_cls(career_page, initial_response=response)
        Log.warning(f"No ATS scraper matched for {career_page.url}")
        return None

    @classmethod
    def _deactivation_status(
        cls,
        response,
        career_page: CareerPage,
    ) -> int | None:
        status_code = response.status_code
        if status_code in {403, 404, 410}:
            return status_code

        if any(
            getattr(entry, "status_code", None) == 301 for entry in response.history
        ):
            final_host = urlparse(response.url or "").hostname or ""
            if _host_matches_suffix(final_host, _DEACTIVATE_REDIRECT_HOST_SUFFIXES):
                return 301
            Log.warning(
                f"{cls.__name__}: 301 redirect for {career_page.url} "
                f"ended at {response.url}, not deactivating"
            )

        return None


def _host_matches_suffix(hostname: str, suffixes: tuple[str, ...]) -> bool:
    if not hostname:
        return False
    for suffix in suffixes:
        if hostname == suffix or hostname.endswith(f".{suffix}"):
            return True
    return False
