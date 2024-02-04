from datetime import datetime
from typing import Optional

from pydantic import Extra
from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel, func


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
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            default=default_now,
            server_default=func.now(),
            index=True,
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            default=None,
            index=True,
            onupdate=default_now,
        )
    )
    deleted_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            index=True,
        )
    )

    deleted: bool = Field(nullable=False, index=True, default=False)

    def delete(self):
        self.deleted = True
        self.deleted_at = datetime.utcnow()

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True
        extra = Extra.ignore
        error_msg_templates = {
            "type_error.none.not_allowed": "Value is missing",
        }
