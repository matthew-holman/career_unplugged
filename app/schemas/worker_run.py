from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class WorkerRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    run_id: str
    worker_name: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    summary: dict[str, Any] | None = None
    errors: list[str] | None = None


class WorkerRunFilter(BaseModel):
    status: str | None = None
    worker_name: str | None = None
    started_at_gte: datetime | None = None
    started_at_lte: datetime | None = None
