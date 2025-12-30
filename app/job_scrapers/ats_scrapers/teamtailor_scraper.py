from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from mypy.checkexpr import Optional

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import JobPost, Location, Source
from app.log import Log
from app.utils.country_resolver import CountryResolver


@dataclass(frozen=True)
class JobCardMetadata:
    department: Optional[str]
    location_raw: Optional[str]
    work_mode_raw: Optional[str]


class TeamTailorScraper(AtsScraper):

    @property
    def source_name(self) -> Source:
        return Source.TEAMTAILOR

    @classmethod
    def supports(cls, url: str) -> bool:
        """
        Return True if the given URL belongs to a Teamtailor-powered site.
        """
        try:
            response = TeamTailorScraper._fetch_page(url)
            if response:
                html = response.text.lower()
            else:
                return False
        except Exception as e:
            Log.warning(f"Failed to fetch {url} for ATS detection: {e}")
            return False

        # We are looking for a Teamtailor page with a teamtailor job list,
        # other job lists are supported on Teamtailor pages.
        if "teamtailor" in html and 'id="jobs_list_container"' in html:
            Log.debug(f"Detected Teamtailor page with Teamtailor jobs list on {url}")
            return True

        return False

    def find_job_cards(self, soup: BeautifulSoup) -> list[Tag]:
        jobs_list = soup.find("ul", id="jobs_list_container")
        if not jobs_list:
            return []
        return jobs_list.find_all("li", recursive=False)

    def parse_job_card(self, card: Tag) -> Optional[JobPost]:
        link = card.find("a", href=True)
        if not link:
            return None

        title = link.get_text(strip=True)
        job_url = urljoin(self.career_page.url, link["href"])

        metadata = self._extract_job_metadata(card)

        city, country = self._parse_location(metadata.location_raw)

        return JobPost(
            title=title,
            company_name=self.company_name(),
            company_url=self.career_page.url,
            location=Location(city=city, country=country),
            date_posted=None,
            job_url=job_url,
            job_type=None,
            description=None,
            remote_status=self.parse_remote_status(metadata.work_mode_raw),
            source=self.source_name,
        )

    def _extract_job_metadata(self, li: Tag) -> JobCardMetadata:
        """
        Teamtailor job card metadata typically looks like:
          <span>Dept</span> · <span>Location</span> · <span>Hybrid</span>
        But Dept may be missing:
          <span>Location</span> · <span>Hybrid</span>
        Also: icon spans can be nested inside the work-mode span.
        """
        metadata_container = li.find(
            "div", class_=lambda c: isinstance(c, str) and "mt-1" in c.split()
        )
        if not metadata_container:
            return JobCardMetadata(
                department=None, location_raw=None, work_mode_raw=None
            )

        content_spans = self._get_direct_content_spans(metadata_container)

        # Split into "work mode" vs "other tokens" by content (not position)
        tokens: list[str] = []
        work_mode_raw: Optional[str] = None

        for text in content_spans:
            # if it looks like Hybrid/Remote/Onsite, treat it as work mode
            if self.parse_remote_status(text) is not None:
                work_mode_raw = text
                continue
            tokens.append(text)

        # tokens now contains dept/location-ish data
        if len(tokens) == 0:
            return JobCardMetadata(
                department=None, location_raw=None, work_mode_raw=work_mode_raw
            )

        if len(tokens) == 1:
            # e.g. ["London"]
            return JobCardMetadata(
                department=None, location_raw=tokens[0], work_mode_raw=work_mode_raw
            )

        # e.g. ["Commercial", "Paris"] or ["Software Development", "Kaunas, Vilnius"]
        return JobCardMetadata(
            department=tokens[0], location_raw=tokens[1], work_mode_raw=work_mode_raw
        )

    @staticmethod
    def _get_direct_content_spans(metadata_container: Tag) -> list[str]:
        """
        Returns cleaned text from direct child <span> elements,
        excluding separator spans ("·") and empty spans.
        Uses get_text(" ", strip=True) to flatten nested icon spans safely.
        """

        def clean(dirt_text: str) -> str:
            return " ".join(dirt_text.split()).strip()

        results: list[str] = []
        for span in metadata_container.find_all("span", recursive=False):
            text = clean(span.get_text(" ", strip=True))
            if not text or text == "·":
                continue
            results.append(text)
        return results

    @staticmethod
    def _parse_location(
        location_raw: Optional[str],
    ) -> tuple[Optional[str], Optional[str]]:
        if not location_raw:
            return None, None

        city: Optional[str] = None
        country: Optional[str] = None

        location = location_raw.split(",")[0].strip() if location_raw else None

        if location:
            country = CountryResolver.resolve_country(location)

        if country:
            city = location
        else:
            country = location

        return city, country
