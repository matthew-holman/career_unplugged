import datetime

from sqlmodel import Field

from app.job_scrapers.scraper import RemoteStatus, Source
from app.models.base_model import BaseModel


class JobBase(BaseModel, table=False):  # type: ignore
    title: str = Field(
        default=None,
        primary_key=False,
    )
    company: str = Field(nullable=False, primary_key=False)
    country: str | None = Field(nullable=True, primary_key=False)
    city: str | None = Field(default=None)
    applied: bool = Field(nullable=False, default=False)
    listing_remote: RemoteStatus | None = Field(
        nullable=True, primary_key=False, default=None
    )
    listing_date: datetime.date | None = Field(
        nullable=True, primary_key=False, default=None
    )
    true_remote: bool | None = Field(nullable=False, default=False)
    analysed: bool = Field(nullable=True, default=False)
    remote_flag_reason: str | None = Field(
        default=None,
        description="Reason this job was flagged as remote (pattern match, location, etc.)",
    )
    positive_keyword_match: bool = Field(nullable=True, default=False)
    negative_keyword_match: bool = Field(nullable=True, default=False)
    source: Source = Field(nullable=False, default=Source.LINKEDIN)
    source_url: str = Field(nullable=False, primary_key=False, unique=True)


class Job(JobBase, table=True):  # type: ignore
    id: int = Field(default=None, primary_key=True)


class JobCreate(JobBase, table=False):  # type: ignore
    pass


class JobRead(JobBase, table=False):  # type: ignore
    id: int
