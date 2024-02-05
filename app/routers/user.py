from fastapi import APIRouter, Depends
from sqlmodel import Session
from starlette import status

from app.db.db import get_db
from app.handlers.user import UserHandler
from app.models import User

INTERFACE = "user"

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
    "/",
    status_code=status.HTTP_200_OK,
    response_model=User,
)
def get_user(
    db_session: Session = Depends(get_db),
) -> User:
    user_handler = UserHandler(db_session)
    user = user_handler.get(email="mholman000@gmail.com")
    if user:
        return user
    user = User()
    user.email = "mholman000@gmail.com"
    user.name = "matthew holman"
    return user_handler.create(user=user)
