from http.client import HTTPException

from fastapi import APIRouter, Depends
from sqlmodel import Session
from starlette import status

from app.db.db import get_db
from app.handlers.job import JobHandler
from app.models.job import JobRead

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
