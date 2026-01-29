from __future__ import annotations

from pydantic import BaseModel


class AtsSyncRequest(BaseModel):
    career_page_ids: list[int] | None = None
    max_age_hours: int | None = None
    include_inactive: bool = False


class LinkedinSyncRequest(BaseModel):
    pass


class SyncAllRequest(BaseModel):
    career_page_ids: list[int] | None = None
    max_age_hours: int | None = None
    include_inactive: bool = False
