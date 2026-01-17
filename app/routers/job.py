from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from starlette import status

from app.auth.current_user import CurrentUser, get_current_user
from app.db.db import get_db
from app.filters.job import JobFilter
from app.handlers.job import JobHandler
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
    job = job_handler.get_for_user(job_id=job_id, user_id=current_user.id)
    if job:
        return job
    else:
        raise HTTPException()


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
    return job_handler.list_for_user(filters=filters, user_id=current_user.id)


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
