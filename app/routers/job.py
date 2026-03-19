from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from starlette import status

from app.auth.current_user import CurrentUser, get_current_user
from app.db.db import get_db
from app.filters.job import JobFilter
from app.handlers.job import JobHandler
from app.handlers.job_tag import JobTagHandler
from app.models.job_tag import JobTagRead
from app.schemas.job import (
    JobWithUserStateRead,
    UserJobStateRead,
    UserJobStateUpdate,
)

INTERFACE = "job"

router = APIRouter(
    prefix=f"/{INTERFACE}",
    tags=[INTERFACE.capitalize()],
    dependencies=[Depends(get_current_user)],
    responses={
        400: {"detail": "Error details"},
        401: {"detail": "Access token was not provided"},
        403: {"detail": "Not authenticated"},
        404: {"detail": "Error details"},
    },
)


def _attach_tags(
    jobs: list[JobWithUserStateRead], tag_handler: JobTagHandler
) -> list[JobWithUserStateRead]:
    """Batch-load tags for a list of jobs and attach them. Single extra query, no N+1."""
    if not jobs:
        return jobs
    job_ids = [j.id for j in jobs]
    raw_tags = tag_handler.get_tags_for_jobs(job_ids)
    tags_by_job: dict[int, list[JobTagRead]] = {}
    for tag in raw_tags:
        tags_by_job.setdefault(tag.job_id, []).append(JobTagRead.model_validate(tag))
    return [
        job.model_copy(update={"tags": tags_by_job.get(job.id, [])}) for job in jobs
    ]


@router.get(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    response_model=JobWithUserStateRead,
)
def get_job(
    job_id: int,
    current_user: CurrentUser,
    db_session: Session = Depends(get_db),
) -> JobWithUserStateRead:
    job_handler = JobHandler(db_session)
    tag_handler = JobTagHandler(db_session)
    job = job_handler.get_for_user(job_id=job_id, user_id=current_user.id)
    if not job:
        raise HTTPException()
    return _attach_tags([job], tag_handler)[0]


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=List[JobWithUserStateRead],
)
def list_jobs(
    filters: Annotated[JobFilter, Query()],
    current_user: CurrentUser,
    db_session: Session = Depends(get_db),
) -> List[JobWithUserStateRead]:
    job_handler = JobHandler(db_session)
    tag_handler = JobTagHandler(db_session)
    jobs = job_handler.list_for_user(filters=filters, user_id=current_user.id)
    return _attach_tags(jobs, tag_handler)


@router.put(
    "/{job_id}/state",
    status_code=status.HTTP_200_OK,
    response_model=UserJobStateRead,
)
def upsert_job_state(
    job_id: int,
    state: UserJobStateUpdate,
    current_user: CurrentUser,
    db_session: Session = Depends(get_db),
) -> UserJobStateRead:
    job_handler = JobHandler(db_session)
    return job_handler.upsert_user_job_state(
        user_id=current_user.id,
        job_id=job_id,
        state=state,
    )
