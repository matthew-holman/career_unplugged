from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, select

from app.db.db import upsert
from app.models.user import User

USER_UPSERT_CONSTRAINT = "ix_user_email"
USER_UPSERT_EXCLUDE: set[str] = {"id", "created_at", "updated_at", "deleted_at"}


@dataclass
class UserHandler:
    db_session: Session

    def get(self, email: str) -> Optional[User]:
        statement = select(User).where(User.email == email)
        user = self.db_session.exec(statement).first()
        return user

    def create(self, user: User) -> User:
        self.db_session.add(user)
        self.db_session.commit()
        self.db_session.refresh(user)
        return user

    def save(self, user: User) -> None:
        upsert(
            model=User,
            db_session=self.db_session,
            data_iter=[user],
            index_elements=["email"],
            exclude_columns=USER_UPSERT_EXCLUDE,
        )
        self.db_session.flush()
