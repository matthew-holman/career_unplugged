from dataclasses import dataclass
from typing import Iterable, Optional, cast

from bs4 import BeautifulSoup, Tag

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import JobPost, Location, RemoteStatus, Source
from app.log import Log


@dataclass(frozen=True)
class GreenhouseBoardJobCard:
    department: Optional[str]
    title: str
    location_raw: Optional[str]
    remote_status: Optional[RemoteStatus]
    job_url: str


class GreenHouseBoardScraper(AtsScraper):

    @property
    def source_name(self) -> Source:
        return Source.GREENHOUSE_BOARD

    @classmethod
    def supports(cls, soup: BeautifulSoup) -> bool:
        if soup.select_one("div.job-posts"):
            return True
        if soup.select_one('a[href*="job-boards.greenhouse.io"]'):
            return True
        return False

    def find_job_cards(self, soup: BeautifulSoup) -> Iterable[object]:
        job_posts_container = soup.select_one("div.job-posts")
        if not job_posts_container:
            Log.warning(
                f"Greenhouse board: div.job-posts not found on {self.career_page.url}"
            )
            return []

        rows = job_posts_container.select("tr.job-post")
        if not rows:
            rows = job_posts_container.select("tr.opening")

        return list(rows)

    def parse_job_card(self, card: object) -> Optional[JobPost]:

        if not isinstance(card, Tag):
            return None
        card = cast(Tag, card)

        parsed = self._parse_greenhouse_board_job_card(card)
        if not parsed:
            return None

        city, country = AtsScraper.parse_location(parsed.location_raw)

        return JobPost(
            title=parsed.title,
            company_name=self.career_page.company_name,
            company_url=self.career_page.url,
            location=Location(city=city, country=country),
            date_posted=None,
            job_url=parsed.job_url,
            job_type=None,
            description=None,
            remote_status=parsed.remote_status,
            source=self.source_name,
        )

    @staticmethod
    def _parse_greenhouse_board_job_card(row: Tag) -> Optional[GreenhouseBoardJobCard]:
        link = row.select_one("a[href]")
        if not link:
            return None

        job_url = (link.get("href") or "").strip()
        if not job_url:
            return None

        title_tag = link.select_one("p.body--medium") or link.select_one("p")
        title = (
            title_tag.get_text(" ", strip=True)
            if title_tag
            else link.get_text(" ", strip=True)
        )
        title = " ".join(title.split()).strip()

        location_tag = link.select_one("p.body__secondary.body--metadata")
        location_raw = location_tag.get_text(" ", strip=True) if location_tag else None

        remote_status = AtsScraper.extract_remote_from_location(location_raw)

        department = None
        department_wrapper = row.find_parent(
            "div", class_="job-posts--table--department"
        )
        if department_wrapper:
            h3 = department_wrapper.select_one("h3.section-header")
            if h3:
                department = h3.get_text(" ", strip=True)

        return GreenhouseBoardJobCard(
            department=department,
            title=title,
            location_raw=location_raw,
            remote_status=remote_status,
            job_url=job_url,
        )
