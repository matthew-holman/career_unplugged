from __future__ import annotations

from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import JobPost, RemoteStatus, Source
from app.log import Log

BAMBOO_HOST_SUFFIX = ".bamboohr.com"


class BambooHrScraper(AtsScraper):
    @property
    def source_name(self) -> Source:
        return Source.BAMBOO

    @classmethod
    def supports(cls, *, url: str, soup: BeautifulSoup) -> bool:
        hostname = urlparse(url).hostname or ""
        return hostname.endswith(BAMBOO_HOST_SUFFIX)

    def find_job_cards(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        base_url = self.career_page.url.rstrip("/")
        list_url = urljoin(f"{base_url}/", "careers/list")

        Log.info(f"Fetching {self.__class__.__name__} jobs from {list_url}")

        response = self._fetch_page(list_url)

        if not response or not (200 <= response.status_code < 300):
            Log.warning(f"Failed to fetch {list_url}")
            return []

        try:
            data = response.json()
        except ValueError:
            Log.warning(f"Invalid JSON from {list_url}")
            return []

        jobs = data.get("result", [])
        if not isinstance(jobs, list):
            return []

        return [job for job in jobs if isinstance(job, dict)]

    def parse_job_card(self, card: object) -> JobPost | None:
        if not isinstance(card, dict):
            return None

        title = (card.get("jobOpeningName") or "").strip()
        job_id = str(card.get("id") or "").strip()
        if not title or not job_id:
            return None

        job_url = urljoin(f"{self.career_page.url.rstrip('/')}/", f"careers/{job_id}")

        location_hint = self._extract_location_hint_from_json(card)

        parts = [
            title,
            card.get("departmentLabel"),
            card.get("employmentStatusLabel"),
            location_hint,
            str(card.get("isRemote") or ""),
        ]
        card_text = " ".join([part for part in parts if part])

        location, remote_status = self.extract_location_and_remote_status(
            card_text=card_text,
            location_hint=location_hint,
        )

        if card.get("isRemote") is True:
            remote_status = RemoteStatus.REMOTE

        return JobPost(
            title=title,
            company_name=self.career_page.company_name,
            company_url=self.career_page.url,
            location=location,
            date_posted=None,
            job_url=job_url,
            job_type=None,
            description=None,
            remote_status=remote_status,
            source=self.source_name,
        )

    @staticmethod
    def _extract_location_hint_from_json(card: dict[str, Any]) -> str | None:
        primary = card.get("location")
        fallback = card.get("atsLocation")

        for candidate in (primary, fallback):
            if not isinstance(candidate, dict):
                continue
            city = candidate.get("city")
            state = candidate.get("state")
            country = candidate.get("country")
            parts = [part for part in [city, state, country] if part]
            if parts:
                return ", ".join(parts)

        return None
