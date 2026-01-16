from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session, select
from starlette import status

from app.db.db import get_db
from app.models.user import User


def get_current_user(
    db_session: Session = Depends(get_db),
    x_user_id: Annotated[int | None, Header(alias="X-User-Id")] = None,
) -> User:
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="X-User-Id header required",
        )

    user = db_session.exec(select(User).where(User.id == x_user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid user",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
