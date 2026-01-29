# app/models/career_page.py
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class CareerPageBase(SQLModel, table=False):  # type: ignore
    company_name: Optional[str] = Field(default=None)
    url: str = Field(nullable=False, unique=True)
    active: bool = Field(default=True, nullable=False)


class CareerPage(CareerPageBase, table=True):  # type: ignore  # type: ignore
    __tablename__ = "career_page"
    id: int = Field(default=None, primary_key=True)
    deactivated_at: datetime | None = Field(default=None)
    last_status_code: int | None = Field(default=None)
    last_synced_at: datetime | None = Field(default=None)


class CareerPageCreate(CareerPageBase, table=False):  # type: ignore
    pass


class CareerPageRead(CareerPageBase, table=False):  # type: ignore
    id: int
