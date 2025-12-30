from typing import Optional

from bs4 import BeautifulSoup, Tag

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import JobPost, Source
from app.log import Log


class GreenHouseScraper(AtsScraper):

    @property
    def source_name(self) -> Source:
        return Source.GREENHOUSE

    @classmethod
    def supports(cls, url: str) -> bool:
        """
        Return True if the given URL belongs to a Greenhouse-jobs list.
        """
        try:
            response = GreenHouseScraper._fetch_page(url)
            if response:
                html = response.text.lower()
            else:
                return False
        except Exception as e:
            Log.warning(f"Failed to fetch {url} for ATS detection: {e}")
            return False

        if "greenhouse-job-board" in html:
            Log.debug("Detected Green House jobs list")
            return True

        return False

    def find_job_cards(self, soup: BeautifulSoup) -> list[Tag]:
        return []

    def parse_job_card(self, card: Tag) -> Optional[JobPost]:
        pass
