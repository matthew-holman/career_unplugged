from __future__ import annotations

from pydantic import BaseModel


class AtsSyncRequest(BaseModel):
    career_page_ids: list[int] | None = None
    max_age_hours: int | None = None
    include_inactive: bool = False
    # Scan low-relevance pages even when they are not yet due a re-check.
    include_low_relevance: bool = False


class LinkedinSyncRequest(BaseModel):
    pass


class SyncAllRequest(BaseModel):
    career_page_ids: list[int] | None = None
    max_age_hours: int | None = None
    include_inactive: bool = False
    # Scan low-relevance pages even when they are not yet due a re-check.
    include_low_relevance: bool = False
