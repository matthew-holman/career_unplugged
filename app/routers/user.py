from typing import Annotated, List

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from starlette import status

from app.auth.current_user import CurrentUser, get_current_user
from app.db.db import get_db
from app.filters.user_activity import UserActivityFilter
from app.handlers.job import JobHandler
from app.schemas.job import JobWithUserStateRead

INTERFACE = "user"

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
    "/activity",
    status_code=status.HTTP_200_OK,
    response_model=List[JobWithUserStateRead],
)
def list_user_activity(
    filters: Annotated[UserActivityFilter, Query()],
    current_user: CurrentUser,
    db_session: Session = Depends(get_db),
) -> List[JobWithUserStateRead]:
    return JobHandler(db_session).list_user_activity(
        filters=filters, user_id=current_user.id
    )
