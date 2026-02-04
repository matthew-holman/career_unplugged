from datetime import date
from typing import Iterable, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import JobPost, Source
from app.log import Log

HIBOB_HOST_SUFFIX = "careers.hibob.com"


class HiBobScraper(AtsScraper):

    @property
    def source_name(self) -> Source:
        return Source.HIBOB

    @classmethod
    def supports(cls, *, url: str, soup: BeautifulSoup) -> bool:
        hostname = urlparse(url).hostname or ""
        return hostname.endswith(HIBOB_HOST_SUFFIX)

    def find_job_cards(self, soup: BeautifulSoup) -> Iterable[object]:
        api_url = self._build_api_url(self.career_page.url)
        response = self._fetch_hibob_api(api_url)
        if not response:
            return []
        try:
            payload = response.json()
        except ValueError:
            Log.warning(
                f"{self.__class__.__name__}: failed to decode JSON from {api_url}"
            )
            return []

        job_ads = payload.get("jobAdDetails")
        if not isinstance(job_ads, list):
            Log.warning(
                f"{self.__class__.__name__}: jobAdDetails missing for {api_url}"
            )
            return []
        return job_ads

    def parse_job_card(self, card: object) -> Optional[JobPost]:
        if not isinstance(card, dict):
            return None

        title = card.get("title")
        if not isinstance(title, str) or not title.strip():
            return None

        job_url = self._extract_job_url(card)
        if not job_url:
            Log.warning(
                f"{self.__class__.__name__}: missing job url for "
                f"{self.career_page.url}"
            )
            return None

        location_raw = None
        site = card.get("site")
        if isinstance(site, str) and site.strip():
            location_raw = site.strip()
        country = card.get("country")
        if not location_raw and isinstance(country, str):
            location_raw = country.strip()

        workspace_type = card.get("workspaceType")
        card_text_parts = [title, location_raw, workspace_type]
        card_text = " ".join(part for part in card_text_parts if part)
        location, remote_status = AtsScraper.extract_location_and_remote_status(
            card_text=card_text, location_hint=location_raw
        )

        published_at = card.get("publishedAt")
        listing_date = self._parse_published_date(published_at)

        employment_type = card.get("employmentType")
        job_type = AtsScraper.parse_job_type(employment_type)

        description = card.get("description")
        if not isinstance(description, str):
            description = None

        return JobPost(
            title=title.strip(),
            company_name=self.career_page.company_name,
            company_url=self.career_page.url,
            location=location,
            date_posted=listing_date,
            job_url=job_url,
            job_type=[job_type] if job_type else None,
            description=description,
            remote_status=remote_status,
            listing_date=listing_date,
            source=self.source_name,
        )

    @staticmethod
    def _build_api_url(base_url: str) -> str:
        return base_url.rstrip("/") + "/api/job-ad"

    @classmethod
    def _extract_company_identifier(cls, url: str) -> Optional[str]:
        hostname = urlparse(url).hostname or ""
        if not hostname.endswith(HIBOB_HOST_SUFFIX):
            return None
        slug = hostname.split(".", 1)[0].strip()
        return slug or None

    def _fetch_hibob_api(self, api_url: str):
        company_identifier = self._extract_company_identifier(self.career_page.url)
        if not company_identifier:
            Log.warning(
                f"{self.__class__.__name__}: missing company identifier for "
                f"{self.career_page.url}"
            )
            return None

        headers = {"companyidentifier": company_identifier}
        return self._fetch_page(api_url, headers=headers)

    def _extract_job_url(self, card: dict) -> Optional[str]:
        for key in ("jobAdUrl", "jobUrl", "url"):
            value = card.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        job_id = card.get("id")
        if isinstance(job_id, str) and job_id.strip():
            return self.career_page.url.rstrip("/") + f"/job-ad/{job_id.strip()}"

        return None

    def _fetch_job_description(self, job_url: str) -> Optional[str]:
        job_id = self._extract_job_id(job_url)
        if not job_id:
            Log.warning(f"{self.__class__.__name__}: missing job id for {job_url}")
            return None

        api_url = (
            self.career_page.url.rstrip("/") + f"/api/job-ad/{job_id}/application-form"
        )
        response = self._fetch_hibob_api(api_url)
        if not response:
            return None
        try:
            payload = response.json()
        except ValueError:
            Log.warning(
                f"{self.__class__.__name__}: failed to decode JSON from {api_url}"
            )
            return None

        for key in ("description", "jobAdDescription", "jobDescription"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        return None

    @staticmethod
    def _extract_job_id(job_url: str) -> Optional[str]:
        parsed = urlparse(job_url)
        path = (parsed.path or "").strip("/")
        if not path:
            return None

        if "/job-ad/" in path:
            return path.split("/job-ad/", 1)[1].split("/", 1)[0]

        parts = path.split("/")
        return parts[-1] if parts else None

    @staticmethod
    def _parse_published_date(value: object) -> date | None:
        if not isinstance(value, str) or not value.strip():
            return None
        cleaned = value.strip()
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        try:
            return date.fromisoformat(cleaned[:10])
        except ValueError:
            return None
