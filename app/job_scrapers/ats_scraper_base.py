import re
import unicodedata

from abc import abstractmethod
from typing import Iterable, Optional

import requests

from bs4 import BeautifulSoup
from requests import Response
from requests.exceptions import ConnectionError, ReadTimeout, Timeout

from app.job_scrapers.scraper import (
    JobPost,
    JobResponse,
    JobType,
    Location,
    RemoteStatus,
    Source,
)
from app.log import Log
from app.models.career_page import CareerPage
from app.utils.locations.location_parser import LocationParser


class AtsScraper:
    """
    Base interface for all ATS scrapers.
    Each subclass must implement:
      - supports(url: str, soup: BeautifulSoup) -> bool
      - scrape(scraper_input: Optional[ScraperInput]) -> JobResponse
    """

    def __init__(
        self,
        career_page: CareerPage,
        *,
        initial_response: Optional[Response] = None,
    ):
        self.career_page = career_page
        self._initial_response = initial_response

    @property
    @abstractmethod
    def source_name(self) -> Source:
        """Human-readable source name, e.g. 'linkedin', 'teamtailor'."""
        pass

    @classmethod
    @abstractmethod
    def supports(cls, *, url: str, soup: BeautifulSoup) -> bool:
        """Return True if this scraper can handle the given page soup."""
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

        response = self._initial_response or self._fetch_jobs_page(jobs_url)
        if not response:
            return JobResponse(jobs=[])

        if response.status_code != 200:
            Log.warning(f"Failed to fetch {jobs_url}: {response.status_code}")
            return JobResponse(jobs=[])

        soup = BeautifulSoup(response.text, "html.parser")

        return self._scrape_from_soup(soup, jobs_url)

    def _scrape_from_soup(self, soup: BeautifulSoup, jobs_url: str) -> JobResponse:
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

    @classmethod
    def _fetch_jobs_page(cls, jobs_url: str) -> Optional[Response]:
        scraper_name = cls.__name__
        if not jobs_url:
            Log.warning(f"Could not resolve {scraper_name} jobs page from: {jobs_url}")
            return None

        Log.info(f"Fetching {scraper_name} jobs from {jobs_url}")
        return AtsScraper._fetch_page(jobs_url)

    @staticmethod
    def _fetch_page(
        url: str,
        *,
        return_errors: bool = False,
        headers: dict[str, str] | None = None,
    ) -> Optional[Response]:
        request_headers = {"User-Agent": "Mozilla/5.0"}
        if headers:
            request_headers.update(headers)
        try:
            response = requests.get(
                url,
                headers=request_headers,
                # Tuple timeout: (connect_timeout, read_timeout)
                timeout=(5, 10),
            )
        except ReadTimeout:
            Log.warning(f"Read timeout while fetching {url}")
            return None
        except Timeout:
            # Covers connect timeout + other timeout variants
            Log.warning(f"Timeout while fetching {url}")
            return None
        except ConnectionError as exc:
            if return_errors:
                raise ConnectionError from exc
            else:
                Log.warning(f"Connection error while fetching {url}: {exc}")
                return None
        except requests.RequestException as exc:
            # Catch-all for requests/urllib3 errors (DNS, SSL, etc.)
            Log.warning(f"Request error while fetching {url}: {exc}")
            return None

        if response.status_code != 200 and not return_errors:
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
    def extract_location_and_remote_status(
        cls,
        *,
        card_text: str,
        location_hint: str | None = None,
    ) -> tuple[Location | None, RemoteStatus]:
        """
        Canonical location + remote status extraction.
        Scrapers should not implement their own location parsing once this exists.
        """
        signal_text = cls._build_signal_text(card_text, location_hint)
        remote_status = cls._detect_remote_status(signal_text)

        location_candidate = LocationParser.pick_location_candidate(
            card_text, location_hint
        )
        if location_candidate:
            city, country = cls.parse_location(location_candidate)
            if city or country:
                return Location(city=city, country=country), remote_status
            Log.warning(
                "unable to find location based on location hint " f"{location_hint}"
            )

        Log.warning(
            "unable to find location based on location hint " f"{location_hint}"
        )

        return None, remote_status

    @classmethod
    def _build_signal_text(cls, card_text: str, location_hint: str | None) -> str:
        parts = [card_text.strip()]
        if location_hint:
            parts.append(location_hint.strip())
        return " ".join(part for part in parts if part)

    @classmethod
    def _detect_remote_status(cls, text: str) -> RemoteStatus:
        normalized = cls._normalize_scraped_text(text)
        markers: set[RemoteStatus] = set()

        if re.search(r"\b(remote|fully remote|100% remote)\b", normalized):
            markers.add(RemoteStatus.REMOTE)
        if re.search(r"\bhybrid\b", normalized):
            markers.add(RemoteStatus.HYBRID)
        if re.search(r"\b(on[\s-]?site|onsite|in office)\b", normalized):
            markers.add(RemoteStatus.ONSITE)

        if len(markers) > 1:
            return RemoteStatus.UNKNOWN
        if len(markers) == 1:
            return next(iter(markers))

        return RemoteStatus.UNKNOWN

    def company_name(self) -> str:
        return self.career_page.company_name or "Unknown"

    @classmethod
    def parse_location(
        cls,
        location_raw: Optional[str],
        *,
        prefer_europe: bool = True,
    ) -> tuple[Optional[str], Optional[str]]:
        return LocationParser.parse_location(location_raw, prefer_europe=prefer_europe)
