import re
import unicodedata

from abc import abstractmethod
from typing import Iterable, Optional

import requests

from bs4 import BeautifulSoup
from requests import Response

from app.job_scrapers.scraper import JobPost, JobResponse, JobType, RemoteStatus, Source
from app.log import Log
from app.models.career_page import CareerPage


class AtsScraper:
    """
    Base interface for all ATS scrapers.
    Each subclass must implement:
      - supports(url: str) -> bool
      - scrape(scraper_input: Optional[ScraperInput]) -> JobResponse
    """

    def __init__(self, career_page: CareerPage):
        self.career_page = career_page

    @property
    @abstractmethod
    def source_name(self) -> Source:
        """Human-readable source name, e.g. 'linkedin', 'teamtailor'."""
        pass

    @classmethod
    @abstractmethod
    def supports(cls, url: str) -> bool:
        """Return True if this scraper can handle the given URL."""
        raise NotImplementedError

    @abstractmethod
    def find_job_cards(self, soup: BeautifulSoup) -> Iterable[object]:
        raise NotImplementedError

    @abstractmethod
    def parse_job_card(self, card: object) -> Optional[JobPost]:
        raise NotImplementedError

    def scrape(self) -> JobResponse:
        jobs_url = self.career_page.url
        if not jobs_url:
            Log.warning(f"Could not resolve jobs index URL for {self.career_page.url}")
            return JobResponse(jobs=[])

        response = self._fetch_jobs_page(jobs_url)
        if not response:
            return JobResponse(jobs=[])

        soup = BeautifulSoup(response.text, "html.parser")

        job_cards = list(self.find_job_cards(soup))
        if not job_cards:
            Log.warning(f"No job cards found on {jobs_url}")
            return JobResponse(jobs=[])

        jobs: list[JobPost] = []
        seen_urls: set[str] = set()

        for card in job_cards:
            job_post = self.parse_job_card(card)
            if not job_post:
                continue

            if job_post.job_url in seen_urls:
                continue
            seen_urls.add(job_post.job_url)

            jobs.append(job_post)

        return JobResponse(jobs=jobs)

    @staticmethod
    def _normalize_scraped_text(value: str) -> str:
        value = unicodedata.normalize("NFKD", value)
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        value = value.strip().lower()

        # remove separators but keep spaces for word matching
        value = value.replace("&", " and ")
        value = re.sub(r"[/_|]+", " ", value)
        value = value.replace("-", " ")

        # collapse whitespace
        value = re.sub(r"\s+", " ", value).strip()
        return value

    @staticmethod
    def _fetch_jobs_page(jobs_url: str) -> Optional[Response]:
        if not jobs_url:
            Log.warning(f"Could not resolve Teamtailor jobs page from: {jobs_url}")
            return None

        Log.info(f"Fetching Teamtailor jobs from {jobs_url}")
        return AtsScraper._fetch_page(jobs_url)

    @staticmethod
    def _fetch_page(url: str) -> Optional[Response]:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        if response.status_code != 200:
            Log.warning(f"Failed to fetch {url}: {response.status_code}")
            return None
        return response

    @classmethod
    def parse_job_type(cls, raw: str | None) -> Optional[JobType]:
        """
        Convert a free-text job type (e.g. "Full-time", "Permanent", "Contractor")
        into JobType. Returns None if no confident match.
        """
        if not raw:
            return None

        value = cls._normalize_scraped_text(raw)

        # Strong matches first
        if re.search(r"\bintern(ship)?\b|\btrainee\b|\bplacement\b", value):
            return JobType.INTERNSHIP

        if re.search(r"\bpart time\b|\bparttime\b|\b%?\s*50\b|\b%?\s*60\b", value):
            # Note: percent detection is optional; remove if too magic.
            return JobType.PART_TIME

        if re.search(
            r"\bfull time\b|\bfulltime\b|\bpermanent\b|\bemployee\b|\bregular\b", value
        ):
            return JobType.FULL_TIME

        if re.search(
            r"\bcontract\b|\bcontractor\b|\bfreelance\b|\bconsultant\b|\bself employed\b",
            value,
        ):
            return JobType.CONTRACT

        if re.search(
            r"\btemporary\b|\btemp\b|\bseasonal\b|\bfixed term\b|\blimited term\b",
            value,
        ):
            return JobType.TEMPORARY

        return None

    @classmethod
    def parse_remote_status(cls, raw: str | None) -> Optional[RemoteStatus]:
        """
        Convert a free-text remote label into RemoteStatus.
        Returns None if no confident match.
        """
        if not raw:
            return None

        value = cls._normalize_scraped_text(raw)

        # Order matters
        if value == "remote":
            return RemoteStatus.REMOTE

        if value == "hybrid":
            return RemoteStatus.HYBRID

        if value in {"onsite", "on site", "office"}:
            return RemoteStatus.ONSITE

        return None

    def company_name(self) -> str:
        return self.career_page.company_name or "Unknown"
