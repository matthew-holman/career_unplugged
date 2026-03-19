from enum import Enum

from sqlmodel import Field, SQLModel, UniqueConstraint


class TagCategory(str, Enum):
    TECH_STACK = "tech_stack"
    ROLE_TYPE = "role_type"


class JobTagBase(SQLModel, table=False):  # type: ignore
    job_id: int = Field(nullable=False, foreign_key="job.id", index=True)
    name: str = Field(nullable=False)
    category: TagCategory = Field(nullable=False)


class JobTag(JobTagBase, table=True):  # type: ignore
    __tablename__ = "job_tag"
    __table_args__ = (UniqueConstraint("job_id", "name"),)

    id: int | None = Field(default=None, primary_key=True)


class JobTagRead(SQLModel):
    name: str
    category: TagCategory
