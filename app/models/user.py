from sqlmodel import Field

from app.models.base_model import BaseModel


class UserBase(BaseModel, table=False):  # type: ignore
    name: str = Field(nullable=False)
    email: str = Field(nullable=False, unique=True, index=True)


class User(UserBase, table=True):  # type: ignore
    id: int = Field(default=None, primary_key=True)


class UserCreate(UserBase, table=False):  # type: ignore
    pass


class UserRead(UserBase, table=False):  # type: ignore
    id: int
