from datetime import datetime

from pydantic import Extra
from sqlalchemy import DateTime, func
from sqlmodel import Field, SQLModel


def to_camel(string: str) -> str:
    split_string = string.split("_")
    return split_string[0] + "".join(
        word.capitalize() for word in split_string[1:]
    )


def default_now() -> datetime:
    """Default value for created_at and updated_at columns."""
    return datetime.utcnow()


class BaseModel(SQLModel):
    __abstract__ = True
    created_at: datetime = Field(
        default_factory=datetime.utcnow, nullable=False
    )

    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"onupdate": func.now(), "nullable": True},
    )

    deleted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"nullable": True},
    )

    def delete(self):
        self.deleted = True
        self.deleted_at = datetime.utcnow()

    class Config:
        alias_generator = to_camel
        populate_by_name = True
        extra = Extra.ignore
