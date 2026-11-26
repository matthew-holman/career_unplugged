# app/models/career_page.py
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class CareerPageRelevance(str, Enum):
    """How likely a career page is to list a job worth applying for.

    Set from the locations of the jobs seen on the last scan (most relevant
    job wins). Less relevant pages are scanned less often; see
    ``RELEVANCE_RESCAN_DAYS`` in ``app/search_profile.py``.
    """

    UNKNOWN = "UNKNOWN"  # never scanned, or no job had a usable location
    TARGET = "TARGET"  # a role in a target country, or remote within Europe
    REMOTE_OUTSIDE_EUROPE = "REMOTE_OUTSIDE_EUROPE"  # remote, but only elsewhere
    EUROPE_ONSITE = "EUROPE_ONSITE"  # European roles, none remote or in target
    OUTSIDE_EUROPE = "OUTSIDE_EUROPE"  # every role outside Europe and not remote


class CareerPageScraperStatus(str, Enum):
    """Whether any ATS scraper can read a career page.

    Pages found outside the known ATS hosts (custom domains taken from
    LinkedIn apply links, say) start UNCHECKED. The first scan that fetches the
    page sets SUPPORTED or UNSUPPORTED. UNSUPPORTED pages are only re-checked
    every ``UNSUPPORTED_RECHECK_DAYS`` (``app/search_profile.py``).
    """

    UNCHECKED = "UNCHECKED"
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"


class CareerPageBase(SQLModel, table=False):  # type: ignore
    company_name: Optional[str] = Field(default=None)
    url: str = Field(nullable=False, unique=True)
    active: bool = Field(default=True, nullable=False)
    deactivated_at: datetime | None = Field(default=None)
    last_status_code: int | None = Field(default=None)
    last_synced_at: datetime | None = Field(default=None)
    relevance: CareerPageRelevance = Field(
        default=CareerPageRelevance.UNKNOWN, nullable=False
    )
    # When set, scans no longer change ``relevance``: use it to pin a manual choice.
    relevance_locked: bool = Field(default=False, nullable=False)
    scraper_status: CareerPageScraperStatus = Field(
        default=CareerPageScraperStatus.UNCHECKED, nullable=False
    )
    # When a scan last fetched the page and checked it against the scrapers.
    scraper_checked_at: datetime | None = Field(default=None)


class CareerPage(CareerPageBase, table=True):  # type: ignore  # type: ignore
    __tablename__ = "career_page"
    id: int = Field(default=None, primary_key=True)

    def apply_scanned_relevance(self, relevance: CareerPageRelevance) -> bool:
        """Record the relevance a scan found; return whether it changed.

        A locked page keeps its manual relevance, and an UNKNOWN result (an
        empty board, say) keeps what earlier scans found.
        """
        if self.relevance_locked or relevance == CareerPageRelevance.UNKNOWN:
            return False
        if self.relevance == relevance:
            return False
        self.relevance = relevance
        return True

    def record_scraper_check(self, supported: bool, checked_at: datetime) -> None:
        """Record whether a scraper matched the page on a scan."""
        self.scraper_status = (
            CareerPageScraperStatus.SUPPORTED
            if supported
            else CareerPageScraperStatus.UNSUPPORTED
        )
        self.scraper_checked_at = checked_at


class CareerPageCreate(CareerPageBase, table=False):  # type: ignore
    pass


class CareerPageRead(CareerPageBase, table=False):  # type: ignore
    id: int
