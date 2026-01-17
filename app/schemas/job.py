from pydantic import BaseModel

from app.models.job import JobRead


class JobWithUserStateRead(JobRead):  # type: ignore
    applied: bool = False
    ignored: bool = False


class UserJobStateUpdate(BaseModel):
    applied: bool | None = None
    ignored: bool | None = None


class UserJobStateRead(BaseModel):
    user_id: int
    job_id: int
    applied: bool
    ignored: bool
