from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, select

from app.models.user import User


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
