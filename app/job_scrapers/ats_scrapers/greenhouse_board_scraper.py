from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import JobPost, Location, Source
from app.log import Log
from app.utils.country_resolver import CountryResolver


@dataclass(frozen=True)
class GreenhouseBoardJobCard:
    department: Optional[str]
    title: str
    location_raw: Optional[str]
    job_url: str


class GreenHouseScraper(AtsScraper):

    @property
    def source_name(self) -> Source:
        return Source.GREENHOUSE_BOARD

    @classmethod
    def supports(cls, url: str) -> bool:
        # Keep this intentionally simple as requested.
        # If you later want to be stricter, also check for "div.job-posts" existence.
        try:
            host = urlparse(url.strip()).netloc.lower()
        except ValueError:
            return False
        return host == "job-boards.greenhouse.io"

    def find_job_cards(self, soup: BeautifulSoup) -> list[Tag]:
        """
        On greenhouse board pages each job is a <tr class="job-post">.
        (Your pasted HTML uses <tr class="job-post">; some boards use "opening".)
        """
        job_posts_container = soup.select_one("div.job-posts")
        if not job_posts_container:
            Log.warning(
                f"Greenhouse board: div.job-posts not found on {self.career_page.url}"
            )
            return []

        rows = job_posts_container.select("tr.job-post")
        if not rows:
            # defensive fallback for other variants
            rows = job_posts_container.select("tr.opening")

        return list(rows)

    def parse_job_card(self, job_card: Tag) -> Optional[JobPost]:
        parsed = self._parse_greenhouse_board_job_card(job_card)
        if not parsed:
            return None

        city, country = self._parse_location(parsed.location_raw)

        return JobPost(
            title=parsed.title,
            company_name=self.career_page.company_name,
            company_url=self.career_page.url,
            location=Location(city=city, country=country),
            date_posted=None,
            job_url=parsed.job_url,
            job_type=None,
            description=None,
            remote_status=None,  # greenhouse board snippet doesn't reliably provide this
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

        # Title is usually the first <p> inside the <a>, but be flexible.
        title_tag = link.select_one("p.body--medium") or link.select_one("p")
        title = (
            title_tag.get_text(" ", strip=True)
            if title_tag
            else link.get_text(" ", strip=True)
        )
        title = " ".join(title.split()).strip()

        # Location is usually <p class="body__secondary body--metadata">...</p>
        location_tag = link.select_one("p.body__secondary.body--metadata")
        location_raw = location_tag.get_text(" ", strip=True) if location_tag else None

        # Department is the closest preceding department header
        # <div class="job-posts--table--department"><h3 ...>Engineering</h3> ... <tr class="job-post">...</tr>
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

    @staticmethod
    def _parse_location(
        location_raw: Optional[str],
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Greenhouse board locations often look like:
          "Europe; Latin America; North America"
          "United Kingdom"
          "Thailand"
        So: treat the first token as "city-ish" only if it resolves to a country.
        Otherwise treat it as country (or region).
        """
        if not location_raw:
            return None, None

        first_token = (
            location_raw.split(";")[0].split(",")[0].strip() if location_raw else None
        )
        if not first_token:
            return None, None

        resolved_country = CountryResolver.resolve_country(first_token)
        if resolved_country:
            # first_token is likely a city
            return first_token, resolved_country

        # otherwise treat it as country/region
        return None, first_token
