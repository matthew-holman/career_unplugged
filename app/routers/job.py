from http.client import HTTPException
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from starlette import status

from app.db.db import get_db
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
    title: Optional[str] = None,
    company: Optional[str] = None,
    country: Optional[str] = None,
    city: Optional[str] = None,
    applied: Optional[bool] = None,
    true_remote: Optional[bool] = None,
    analysed: Optional[bool] = None,
    db_session: Session = Depends(get_db),
) -> List[Job]:
    query = select(Job)

    if title is not None:
        query = query.where(Job.title == title)
    if company is not None:
        query = query.where(Job.company == company)
    if country is not None:
        query = query.where(Job.country == country)
    if city is not None:
        query = query.where(Job.city == city)
    if applied is not None:
        query = query.where(Job.applied == applied)
    if true_remote is not None:
        print(true_remote)
        query = query.where(Job.true_remote == true_remote)
    if analysed is not None:
        query = query.where(Job.analysed == analysed)

    results = db_session.exec(query).all()
    return results
