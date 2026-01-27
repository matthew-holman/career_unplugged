from __future__ import annotations

from abc import abstractmethod
from datetime import date
from enum import Enum

from pydantic import BaseModel


class JobType(Enum):
    FULL_TIME = "Full Time"
    PART_TIME = "Part Time"
    INTERNSHIP = "Internship"
    CONTRACT = "Contract"
    TEMPORARY = "Temporary"


class RemoteStatus(str, Enum):
    ONSITE = "ONSITE"
    HYBRID = "HYBRID"
    REMOTE = "REMOTE"


class Source(str, Enum):
    LINKEDIN = "linkedin"
    TEAMTAILOR = "teamtailor"
    GREENHOUSE_BOARD = "greenhouse_board"
    GREENHOUSE_EMBEDDED = "greenhouse_embedded"
    ASHBY = "ashby"
    LEVER = "lever"
    RECRUITEE = "recruitee"
    RIPPLING = "rippling"
    PERSONIO = "personio"


class DescriptionFormat(Enum):
    MARKDOWN = "markdown"
    HTML = "html"


class ScraperInput(BaseModel):
    search_term: str
    location: str
    distance: int | None = None
    remote_status: RemoteStatus | None = None
    job_type: JobType
    easy_apply: bool | None = None
    offset: int = 0
    linkedin_fetch_description: bool = False
    linkedin_company_ids: list[int] | None = None
    description_format: DescriptionFormat | None = DescriptionFormat.MARKDOWN
    results_wanted: int = 15
    hours_old: int = 24


class Location(BaseModel):
    country: str | None = None
    city: str | None = None
    state: str | None = None

    def display_location(self) -> str:
        location_parts = []
        if self.city:
            location_parts.append(self.city)
        if self.state:
            location_parts.append(self.state)
        if isinstance(self.country, str):
            location_parts.append(self.country)
        return ", ".join(location_parts)


class CompensationInterval(Enum):
    YEARLY = "yearly"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    DAILY = "daily"
    HOURLY = "hourly"

    @classmethod
    def get_interval(cls, pay_period):
        interval_mapping = {
            "YEAR": cls.YEARLY,
            "HOUR": cls.HOURLY,
        }
        if pay_period in interval_mapping:
            return interval_mapping[pay_period].value
        else:
            return cls[pay_period].value if pay_period in cls.__members__ else None


class JobPost(BaseModel):
    title: str
    company_name: str | None = None
    job_url: str
    job_url_direct: str | None = None
    location: Location | None

    description: str | None = None
    company_url: str | None = None
    company_url_direct: str | None = None

    job_type: list[JobType] | None = None
    date_posted: date | None = None
    listing_date: date | None = None
    emails: list[str] | None = None
    remote_status: RemoteStatus | None = None

    source: Source | None = None


class JobResponse(BaseModel):
    jobs: list[JobPost] = []


class SearchLocation(BaseModel):
    location: str
    remote: bool


class Scraper:
    def __init__(self, proxy: str | None = None):
        self.proxy = (lambda p: {"http": p, "https": p} if p else None)(proxy)

    @property
    @abstractmethod
    def source_name(self) -> Source:
        """Human-readable source name, e.g. 'linkedin', 'teamtailor'."""
        pass

    def scrape(self, scraper_input: ScraperInput):
        pass
