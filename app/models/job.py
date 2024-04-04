from typing import Optional

from sqlmodel import Field

from app.models.base_model import BaseModel


class JobBase(BaseModel, table=False):  # type: ignore
    title: str = Field(
        default=None,
        primary_key=False,
    )
    company: str = Field(nullable=False, primary_key=False)
    country: str = Field(nullable=False, primary_key=False)
    city: Optional[str] = Field(nullable=True)
    linkedin_url: str = Field(nullable=False, primary_key=False, unique=True)
    applied: bool = Field(nullable=True, default=False)
    remote: Optional[bool] = Field(nullable=True, default=False)
    analysed: bool = Field(nullable=True, default=False)


class Job(JobBase, table=True):  # type: ignore
    id: int = Field(default=None, primary_key=True)


class JobCreate(JobBase, table=False):  # type: ignore
    pass


class JobRead(JobBase, table=False):  # type: ignore
    id: int
