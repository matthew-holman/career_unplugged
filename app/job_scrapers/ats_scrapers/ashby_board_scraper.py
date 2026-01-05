import json
import re
from typing import List, Optional, Any, Iterable
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import Source, JobPost, Location
from app.log import Log

JSON_DATA_VAR = "window.__appData = "

class AshbyBoardScraper(AtsScraper):

    @property
    def source_name(self) -> Source:
        return Source.ASHBY

    @classmethod
    def supports(cls, url: str) -> bool:
        try:
            host = urlparse(url.strip()).netloc.lower()
        except ValueError:
            return False
        return host == "jobs.ashbyhq.com"

    def find_job_cards(self, soup: BeautifulSoup) -> Iterable[object]:
        script_tags = soup.select('script')
        for script in script_tags:
            if JSON_DATA_VAR in script.text:

                pattern = re.compile(
                    re.escape(JSON_DATA_VAR) + r"\s*(.+?);",
                    re.DOTALL,
                )

                match = pattern.search(script.text)
                if not match:
                    return []

                raw_json = match.group(1).strip()
                json_data = json.loads(raw_json)
                if json_data:
                    return json_data.get("jobBoard")['jobPostings']

        Log.warning(f"Couldn't find app data json when scraping page: {self.career_page.url}")
        return []

    def parse_job_card(self, job_card: Tag) -> Optional[JobPost]:
        if not isinstance(job_card, dict):
            return None

        title = job_card.get("title")
        if not isinstance(title, str) or not title.strip():
            return None

        location_raw = job_card.get("locationName")
        if not isinstance(location_raw, str):
            location_raw = ""

        remote_status = AtsScraper.parse_remote_status(job_card.get("workplaceType"))
        city, country = AtsScraper.parse_location(location_raw)

        published_date = job_card.get("publishedDate")
        # Keep whatever your system expects; if JobPost.date_posted is a date,
        # you likely normalize elsewhere. If not, set None.
        date_posted = published_date if isinstance(published_date, str) else None

        job_id = job_card.get("id").strip()
        job_url = f"{self.career_page.url.rstrip('/')}/{job_id}"
        if job_url is None:
            return None

        employment_type = job_card.get("employmentType")
        job_type = AtsScraper.parse_job_type(employment_type)

        return JobPost(
            title=title.strip(),
            company_name=self.career_page.company_name,
            company_url=self.career_page.url,
            location=Location(city=city, country=country),
            date_posted=date_posted,
            job_url=job_url,
            job_type=[job_type],
            description=None,
            remote_status=remote_status,
            source=self.source_name,
        )
