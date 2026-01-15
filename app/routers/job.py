from datetime import datetime, timedelta
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, or_
from sqlmodel import Session, col, select
from starlette import status

from app.db.db import get_db
from app.filters.job import JobFilter
from app.handlers.job import JobHandler
from app.job_scrapers.scraper import RemoteStatus
from app.models.job import Job, JobRead
from app.utils.locations.europe_filter import EuropeFilter

INTERFACE = "job"

router = APIRouter(
    prefix=f"/{INTERFACE}",
    tags=[INTERFACE.capitalize()],
    responses={
        400: {"detail": "Error details"},
        401: {"detail": "Access token was not provided"},
        403: {"detail": "Not authenticated"},
        404: {"detail": "Error details"},
    },
)


@router.get(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    response_model=JobRead,
)
def get_job(job_id: int, db_session: Session = Depends(get_db)) -> JobRead:
    job_handler = JobHandler(db_session)
    job = job_handler.get(job_id=job_id)
    if job:
        return job
    else:
        raise HTTPException()


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=List[Job],
)
def list_jobs(
    filters: Annotated[JobFilter, Query()],
    db_session: Session = Depends(get_db),
) -> List[Job]:
    query = select(Job)

    filter_fields = {
        "title",
        "company",
        "country",
        "city",
        "applied",
        "positive_keyword_match",
        "negative_keyword_match",
        "true_remote",
        "analysed",
        "listing_remote",
        "source",
    }

    provided = filters.model_dump(exclude_none=True)

    for field_name, value in provided.items():
        if field_name in {
            "created_at_gte",
            "created_at_lte",
            "listing_date_gte",
            "listing_date_lte",
            "recent_days",
            "eu_remote",
        }:
            continue
        if field_name in filter_fields:
            query = query.where(getattr(Job, field_name) == value)

    if filters.created_at_gte is not None:
        query = query.where(Job.created_at >= filters.created_at_gte)
    if filters.created_at_lte is not None:
        query = query.where(Job.created_at <= filters.created_at_lte)
    if filters.listing_date_gte is not None:
        query = query.where(col(Job.listing_date) >= filters.listing_date_gte)
    if filters.listing_date_lte is not None:
        query = query.where(col(Job.listing_date) <= filters.listing_date_lte)
    if filters.recent_days is not None:
        cutoff = datetime.utcnow() - timedelta(days=filters.recent_days)
        query = query.where(Job.created_at >= cutoff)
    if filters.eu_remote is True:
        eu_countries = sorted(EuropeFilter.EU_COUNTRIES)
        eu_match = func.lower(col(Job.country)).in_(eu_countries)
        eu_remote = or_(
            col(Job.true_remote).is_(True),
            and_(col(Job.listing_remote) == RemoteStatus.REMOTE, eu_match),
        )
        query = query.where(eu_remote)

    results = db_session.exec(query).all()
    return results


class JobSummary(BaseModel):
    counts_by_source: dict[str, int]
    counts_by_country: dict[str, int]
    counts_by_remote_status: dict[str, int]
    to_review: int
    eu_remote: int
    sweden: int
    new7d: int
    positive_matches: int


@router.get(
    "/summary",
    status_code=status.HTTP_200_OK,
    response_model=JobSummary,
)
def job_summary(db_session: Session = Depends(get_db)) -> JobSummary:
    source_counts = db_session.exec(
        select(Job.source, func.count()).group_by(Job.source)
    ).all()
    country_counts = db_session.exec(
        select(Job.country, func.count()).group_by(Job.country)
    ).all()
    remote_counts = db_session.exec(
        select(Job.listing_remote, func.count()).group_by(Job.listing_remote)
    ).all()

    counts_by_source = {
        (source.value if source else "unknown"): count
        for source, count in source_counts
    }
    counts_by_country = {
        (country if country else "unknown"): count for country, count in country_counts
    }
    counts_by_remote_status = {
        (
            status.value
            if isinstance(status, RemoteStatus)
            else (status if status else "unknown")
        ): count
        for status, count in remote_counts
    }

    eu_countries = sorted(EuropeFilter.EU_COUNTRIES)
    eu_match = func.lower(col(Job.country)).in_(eu_countries)
    eu_remote_filter = or_(
        col(Job.true_remote).is_(True),
        and_(col(Job.listing_remote) == RemoteStatus.REMOTE, eu_match),
    )

    to_review = db_session.exec(
        select(func.count()).where(
            or_(col(Job.applied).is_(False), col(Job.applied).is_(None))
        )
    ).one()
    eu_remote = db_session.exec(select(func.count()).where(eu_remote_filter)).one()
    sweden = db_session.exec(
        select(func.count()).where(func.lower(col(Job.country)) == "sweden")
    ).one()
    cutoff = datetime.utcnow() - timedelta(days=7)
    new7d = db_session.exec(select(func.count()).where(Job.created_at >= cutoff)).one()
    positive_matches = db_session.exec(
        select(func.count()).where(col(Job.positive_keyword_match).is_(True))
    ).one()

    return JobSummary(
        counts_by_source=counts_by_source,
        counts_by_country=counts_by_country,
        counts_by_remote_status=counts_by_remote_status,
        to_review=to_review,
        eu_remote=eu_remote,
        sweden=sweden,
        new7d=new7d,
        positive_matches=positive_matches,
    )
