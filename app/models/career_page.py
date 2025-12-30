# app/models/career_page.py
from typing import Optional

from sqlmodel import Field, SQLModel


class CareerPageBase(SQLModel, table=False):  # type: ignore
    company_name: Optional[str] = Field(default=None)
    url: str = Field(nullable=False, unique=True)
    active: bool = Field(default=True, nullable=False)


class CareerPage(CareerPageBase, table=True):  # type: ignore  # type: ignore
    __tablename__ = "career_page"
    id: int = Field(default=None, primary_key=True)


class CareerPageCreate(CareerPageBase, table=False):  # type: ignore
    pass


class CareerPageRead(CareerPageBase, table=False):  # type: ignore
    id: int
