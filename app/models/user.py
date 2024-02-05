from sqlmodel import Field

from app.models.base_model import BaseModel


class User(BaseModel, table=True):  # type: ignore
    email: str = Field(default=None, primary_key=True)
    name: str = Field(
        nullable=False,
        primary_key=False,
        index=True,
        max_length=20,
    )
