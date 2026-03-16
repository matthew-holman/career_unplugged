from typing import Literal

from app.filters.job import JobFilter


class UserActivityFilter(JobFilter):
    activity: Literal["applied", "ignored", "both"] = "both"
    applied: bool | None = None  # type: ignore
    ignored: bool | None = None  # type: ignore
