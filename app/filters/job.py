from datetime import date, datetime

from pydantic import BaseModel

from app.job_scrapers.scraper import RemoteStatus, Source


class JobFilter(BaseModel):
    title: str | None = None
    company: str | None = None
    country: str | None = None
    city: str | None = None
    positive_keyword_match: bool | None = None
    negative_keyword_match: bool | None = None
    true_remote: bool | None = None
    analysed: bool | None = None
    listing_remote: RemoteStatus | None = None
    source: Source | None = None
    created_at_gte: datetime | None = None
    created_at_lte: datetime | None = None
    listing_date_gte: date | None = None
    listing_date_lte: date | None = None
    eu_remote: bool | None = None
    recent_days: int | None = None
