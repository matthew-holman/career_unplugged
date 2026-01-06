import re
import unicodedata

from abc import abstractmethod
from typing import Iterable, Optional

import requests

from bs4 import BeautifulSoup
from requests import Response
from requests.exceptions import ConnectionError, ReadTimeout, Timeout

from app.job_scrapers.scraper import JobPost, JobResponse, JobType, RemoteStatus, Source
from app.log import Log
from app.models.career_page import CareerPage
from app.utils.locations.country_resolver import CountryResolver
from app.utils.locations.europe_filter import EuropeFilter


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

    @classmethod
    def _fetch_jobs_page(cls, jobs_url: str) -> Optional[Response]:
        scraper_name = cls.__name__
        if not jobs_url:
            Log.warning(f"Could not resolve {scraper_name} jobs page from: {jobs_url}")
            return None

        Log.info(f"Fetching {scraper_name} jobs from {jobs_url}")
        return AtsScraper._fetch_page(jobs_url)

    @staticmethod
    def _fetch_page(url: str) -> Optional[Response]:
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
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
            Log.warning(f"Connection error while fetching {url}: {exc}")
            return None
        except requests.RequestException as exc:
            # Catch-all for requests/urllib3 errors (DNS, SSL, etc.)
            Log.warning(f"Request error while fetching {url}: {exc}")
            return None

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

    @classmethod
    def extract_remote_from_location(
        cls, location_raw: Optional[str]
    ) -> Optional[RemoteStatus]:
        if not location_raw:
            return None

        text = location_raw.lower()

        if "remote" in text:
            return RemoteStatus.REMOTE

        if "hybrid" in text:
            return RemoteStatus.HYBRID

        if "onsite" in text or "on-site" in text or "on site" in text:
            return RemoteStatus.ONSITE

        return None

    def company_name(self) -> str:
        return self.career_page.company_name or "Unknown"

    @classmethod
    def parse_location(
        cls,
        location_raw: Optional[str],
        *,
        prefer_europe: bool = True,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Parse an ATS location string into (city, country_or_region).

        Rules:
          - Remove remote/hybrid/onsite markers, but preserve commas (City, Country).
          - If multi-location (e.g. "Remote, APAC; Remote, Netherlands; ..."):
              - Prefer first European chunk (if prefer_europe=True)
              - Else pick first chunk
          - Interpret "City, Country" when possible.
          - If no resolvable city->country, treat token as country/region.
        """
        if not location_raw:
            return None, None

        normalized = cls._normalize_location(location_raw)
        if not normalized:
            return None, None

        candidates = cls._split_location_candidates(normalized)
        if not candidates:
            return None, None

        primary = cls._pick_primary_candidate(candidates, prefer_europe=prefer_europe)
        if not primary:
            return None, None

        return cls._parse_single_location_candidate(primary)

    # -----------------------
    # Internal helpers
    # -----------------------
    @classmethod
    def _normalize_location(cls, location: str) -> str:
        """
        Keep delimiters needed for parsing (commas/semicolons),
        remove remote/hybrid-ish markers, and normalise whitespace/punctuation.
        """
        text = " ".join(location.strip().split())

        # remove markers (do not remove commas/semicolons)
        # NOTE: order matters: handle multi-word before single-word
        patterns = [
            r"\bfully\s+remote\b",
            r"\bremote[-\s]?first\b",
            r"\bon[-\s]?site\b",
            r"\bonsite\b",
            r"\bhybrid\b",
            r"\bremote\b",
        ]
        for pattern in patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # normalise dashes and comma spacing; keep ';' as separator
        text = text.replace("—", "-").replace("–", "-")
        text = re.sub(r"\s*[-]\s*", " - ", text)
        text = re.sub(r"\s*,\s*", ", ", text)
        text = re.sub(r"\s{2,}", " ", text).strip()

        # trim leftover punctuation created by marker removals
        text = text.strip(" ,;|-")
        return text

    @classmethod
    def _split_location_candidates(cls, normalized: str) -> list[str]:
        """
        Split multi-location strings into candidate chunks.
        Primary separator: ';'
        """
        parts = [cls._clean_part(p) for p in normalized.split(";")]
        return [p for p in parts if p]

    @staticmethod
    def _clean_part(value: str) -> str:
        # strip leading/trailing separators: space, comma, semicolon, pipe, dash
        return re.sub(r"^[\s,;|\-]+|[\s,;|\-]+$", "", value)

    @classmethod
    def _pick_primary_candidate(
        cls,
        candidates: list[str],
        *,
        prefer_europe: bool,
    ) -> Optional[str]:
        if not candidates:
            return None

        if not prefer_europe:
            return candidates[0]

        for candidate in candidates:
            # We pass "country-ish" token into EuropeFilter: prefer right side of comma if present
            countryish = (
                candidate.split(",", 1)[-1].strip() if "," in candidate else candidate
            )
            if EuropeFilter.is_european(countryish):
                return candidate

        return candidates[0]

    @classmethod
    def _parse_single_location_candidate(
        cls, candidate: str
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Parse a single candidate like:
          - "Berlin, Germany"
          - "Netherlands"
          - "Europe"
          - "United States & Canada"
        """
        candidate = candidate.strip()
        if not candidate:
            return None, None

        if "," in candidate:
            left_raw, right_raw = (p.strip() for p in candidate.split(",", 1))
            city = cls._clean_atom(left_raw)
            right = cls._clean_atom(right_raw)

            # If right looks like a known country/region (or can be resolved), treat as country
            if right:
                resolved_right = CountryResolver.resolve_country(right) or right
                # Only treat left as city if right is actually a country (not just any region token)
                # CountryResolver returning something is the strongest signal.
                if CountryResolver.resolve_country(right):
                    return city, resolved_right

            # Otherwise, see if left itself is a city we can resolve
            if city:
                resolved_left = CountryResolver.resolve_country(city)
                if resolved_left:
                    return city, resolved_left

            # Fallback: keep right side as country/region-ish
            return None, right

        token = cls._clean_atom(candidate)
        if not token:
            return None, None

        resolved = CountryResolver.resolve_country(token)
        if resolved:
            # token is city -> country
            return token, resolved

        # token is country/region
        return None, token

    @staticmethod
    def _clean_atom(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        cleaned = " ".join(value.strip().split())
        cleaned = cleaned.strip(" ,;|")
        return cleaned or None
