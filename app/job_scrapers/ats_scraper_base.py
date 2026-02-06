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
from app.utils.locations.country_resolver import CountryResolver
from app.utils.locations.europe_filter import EuropeFilter


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
                raise ConnectionError
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

        location_candidate = cls._pick_location_candidate(card_text, location_hint)
        if location_candidate:
            city, country = cls.parse_location(location_candidate)
            if city or country:
                return Location(city=city, country=country), remote_status

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

    @classmethod
    def _pick_location_candidate(
        cls, card_text: str, location_hint: str | None
    ) -> Optional[str]:
        if location_hint:
            cleaned_hint = cls._clean_location_hint(location_hint)
            if cls._is_location_hint_valid(cleaned_hint):
                return cleaned_hint

        candidate = cls._extract_location_candidate_from_text(card_text)
        if candidate:
            return candidate

        return None

    @classmethod
    def _extract_location_candidate_from_text(cls, text: str) -> Optional[str]:
        if not text:
            return None

        for chunk in re.split(r"[|•·/]+", text):
            if cls._is_location_hint_valid(chunk):
                return cls._clean_location_hint(chunk)

        pattern = re.compile(r"([A-Za-zÀ-ÖØ-öø-ÿ.'\- ]+),\s*([A-Za-zÀ-ÖØ-öø-ÿ.'\- ]+)")
        for match in pattern.finditer(text):
            candidate = f"{match.group(1).strip()}, {match.group(2).strip()}"
            if cls._is_location_hint_valid(candidate):
                return cls._clean_location_hint(candidate)

        return None

    @classmethod
    def _is_location_hint_valid(cls, hint: str) -> bool:
        """
        "Valid" here means: it looks like a specific country or a city/location
        we can resolve to a country, OR one of a few known region tokens (e.g. Europe).
        """
        cleaned = cls._clean_location_hint(hint)
        if not cleaned:
            return False

        lowered = cleaned.lower()
        if re.search(r"\b(eu|emea|europe|european union)\b", lowered):
            return True

        # Handle comma forms by checking both sides against our two primitives:
        # - is_country(token): token is a country name
        # - resolve_country(token): token is a city/location and returns its country
        if "," in cleaned:
            left, right = (p.strip() for p in cleaned.split(",", 1))
            if (
                (right and CountryResolver.is_country(right))
                or (left and CountryResolver.resolve_country(left) is not None)
                or (right and CountryResolver.resolve_country(right) is not None)
            ):
                return True

        if CountryResolver.is_country(cleaned):
            return True

        if CountryResolver.resolve_country(cleaned) is not None:
            return True

        return False

    @classmethod
    def _clean_location_hint(cls, hint: str) -> str:
        # Normalize whitespace first
        cleaned = " ".join(hint.split())

        # Remove parenthetical qualifiers: "(remote)", "(hybrid)", "(onsite)", etc.
        # This removes any (...) including surrounding whitespace
        cleaned = re.sub(r"\s*\([^)]*\)", "", cleaned)

        # Normalize separators
        cleaned = re.sub(r"[·|/]+", ", ", cleaned)
        cleaned = cleaned.replace("—", "-").replace("–", "-")

        # Trim junk punctuation
        cleaned = cleaned.strip(" ,;|-")

        # Canonical normalization (case, accents, etc.)
        cleaned = cls._normalize_location(cleaned)

        lowered = cleaned.lower()
        ignore_tokens = {"head office", "hq", "global", "multiple locations"}
        if lowered in ignore_tokens:
            return ""

        return cleaned

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
            r"\bgreater\b",
            r"\bmetropolitan\b",
            r"\barea\b",
            r"\bregion\b",
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
            # Prefer right side of comma if present (country-ish), else whole token.
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
          - "London, United Kingdom"
          - "Netherlands"
          - "Europe"
          - "United States & Canada"
          - "London" (if resolvable as city -> country)

        Contract assumptions:
          - CountryResolver.is_country(token) == token is a country name
          - CountryResolver.resolve_country(token) returns a country string IFF token is a city/location
        """
        candidate = candidate.strip()
        if not candidate:
            return None, None

        if "," in candidate:
            left_raw, right_raw = (p.strip() for p in candidate.split(",", 1))
            left = cls._clean_atom(left_raw)
            right = cls._clean_atom(right_raw)

            if not left and not right:
                return None, None

            # 1) Classic "City, Country"
            if right and CountryResolver.is_country(right):
                return left, right

            # 2) Left is a city/location -> resolve to country
            if left:
                resolved_left_country = CountryResolver.resolve_country(left)
                if resolved_left_country:
                    return left, resolved_left_country

            # 3) Right is a city/location -> resolve to country (salvage odd formats)
            if right:
                resolved_right_country = CountryResolver.resolve_country(right)
                if resolved_right_country:
                    return right, resolved_right_country

            # 4) Fallback: keep the most country/region-ish side if present.
            return None, right or left

        token = cls._clean_atom(candidate)
        if not token:
            return None, None

        resolved_country = CountryResolver.resolve_country(token)
        if resolved_country:
            return token, resolved_country

        return None, token

    @staticmethod
    def _clean_atom(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        cleaned = " ".join(value.strip().split())
        cleaned = cleaned.strip(" ,;|")
        return cleaned or None
