import re
import unicodedata

from abc import abstractmethod
from typing import Optional

from app.job_scrapers.scraper import JobResponse, JobType, RemoteStatus, Source
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
    def scrape(self) -> JobResponse:
        """Perform the scrape and return a JobResponse."""
        raise NotImplementedError

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
