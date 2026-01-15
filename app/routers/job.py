from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, col, select
from starlette import status

from app.db.db import get_db
from app.filters.job import JobFilter
from app.handlers.job import JobHandler
from app.models.job import Job, JobRead

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
        if field_name in {"created_at_gte", "created_at_lte"}:
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

    results = db_session.exec(query).all()
    return results
