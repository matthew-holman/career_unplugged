from dataclasses import dataclass
from typing import Iterable, Optional, cast
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import JobPost, JobResponse, Source
from app.log import Log


@dataclass(frozen=True)
class GreenhouseBoardJobCard:
    department: Optional[str]
    title: str
    location_raw: Optional[str]
    job_url: str


class GreenHouseBoardScraper(AtsScraper):
    _GREENHOUSE_HOSTS = (
        "job-boards.greenhouse.io",
        "job-boards.eu.greenhouse.io",
    )

    @property
    def source_name(self) -> Source:
        return Source.GREENHOUSE_BOARD

    @classmethod
    def supports(cls, *, url: str, soup: BeautifulSoup) -> bool:
        hostname = urlparse(url).hostname or ""
        if cls._is_greenhouse_host(hostname):
            return True
        if soup.select_one("div.job-posts"):
            return True
        if soup.select_one('a[href*="job-boards.greenhouse.io"]') or soup.select_one(
            'a[href*="job-boards.eu.greenhouse.io"]'
        ):
            return True
        return False

    def scrape(self) -> JobResponse:
        jobs_url = self.career_page.url
        if not jobs_url:
            Log.warning(f"Could not resolve jobs index URL for {self.career_page.url}")
            return JobResponse(jobs=[])

        response = self._initial_response or self._fetch_jobs_page(jobs_url)
        if not response:
            return JobResponse(jobs=[])

        if response.status_code != 200:
            Log.warning(f"Failed to fetch {jobs_url}: {response.status_code}")
            return JobResponse(jobs=[])

        if self._redirected_off_greenhouse(response):
            embed_response = self._fetch_embed_response(jobs_url)
            if not embed_response:
                return JobResponse(jobs=[])
            response = embed_response

        soup = BeautifulSoup(response.text, "html.parser")
        return self._scrape_from_soup(soup, jobs_url)

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
        card_tag = cast(Tag, card)

        parsed = self._parse_greenhouse_board_job_card(card_tag)
        if not parsed:
            return None

        card_text = card_tag.get_text(" ", strip=True)
        location, remote_status = AtsScraper.extract_location_and_remote_status(
            card_text=card_text, location_hint=parsed.location_raw
        )

        return JobPost(
            title=parsed.title,
            company_name=self.career_page.company_name,
            company_url=self.career_page.url,
            location=location,
            date_posted=None,
            job_url=parsed.job_url,
            job_type=None,
            description=None,
            remote_status=remote_status,
            source=self.source_name,
        )

    @classmethod
    def _is_greenhouse_host(cls, hostname: str) -> bool:
        return hostname in cls._GREENHOUSE_HOSTS

    @classmethod
    def _redirected_off_greenhouse(cls, response) -> bool:
        if not response.history:
            return False
        final_host = urlparse(response.url or "").hostname or ""
        return not cls._is_greenhouse_host(final_host)

    @classmethod
    def _extract_slug_from_board_url(cls, url: str) -> Optional[str]:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        if not cls._is_greenhouse_host(hostname):
            return None

        path = (parsed.path or "").strip("/")
        if not path:
            return None
        slug = path.split("/", 1)[0].strip()
        return slug or None

    @staticmethod
    def _build_embed_url(host: str, slug: str) -> str:
        host = host.strip()
        slug = slug.strip()
        return f"https://{host}/embed/job_board?for={slug}"

    def _fetch_embed_response(self, original_url: str):
        slug = self._extract_slug_from_board_url(original_url)
        if not slug:
            Log.warning(
                f"{self.__class__.__name__}: could not extract slug from {original_url}"
            )
            return None

        host = urlparse(original_url).hostname or ""
        if not self._is_greenhouse_host(host):
            Log.warning(
                f"{self.__class__.__name__}: unsupported greenhouse host in "
                f"{original_url}"
            )
            return None

        embed_url = self._build_embed_url(host, slug)
        Log.info(
            f"{self.__class__.__name__}: fetching greenhouse embed fallback "
            f"from {embed_url}"
        )
        return self._fetch_jobs_page(embed_url)

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
            job_url=job_url,
        )
