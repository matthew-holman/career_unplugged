from fastapi import APIRouter, Depends
from sqlmodel import Session
from starlette import status

from app.db.db import get_db
from app.handlers.dashboard import DashboardHandler
from app.schemas.dashboard import JobSummary

INTERFACE = "dashboard"

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
    "/jobs/summary",
    status_code=status.HTTP_200_OK,
    response_model=JobSummary,
)
def jobs_summary(db_session: Session = Depends(get_db)) -> JobSummary:
    return DashboardHandler(db_session).get_jobs_summary()
