from fastapi import APIRouter, Depends
from sqlmodel import Session
from starlette import status

from app.db.db import get_db
from app.models import HelloWorld

INTERFACE = "helloworld"

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
    response_model=HelloWorld,
)
def get_hello_world(
    db_session: Session = Depends(get_db),
) -> HelloWorld:
    hello_world = HelloWorld()
    return hello_world
