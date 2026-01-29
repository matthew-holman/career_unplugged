from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from app.models.base_model import BaseModel


class WorkerRunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class WorkerRunBase(BaseModel, table=False):  # type: ignore
    run_id: str = Field(default_factory=lambda: str(uuid4()), unique=True, index=True)
    worker_name: str = Field(nullable=False)
    status: WorkerRunStatus = Field(nullable=False, default=WorkerRunStatus.PENDING)
    started_at: datetime = Field(nullable=False)
    finished_at: datetime | None = Field(default=None)
    summary: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    errors: list[str] | None = Field(default=None, sa_column=Column(JSONB))


class WorkerRun(WorkerRunBase, table=True):  # type: ignore
    __tablename__ = "worker_run"
    id: int = Field(default=None, primary_key=True)


class WorkerRunRead(WorkerRunBase, table=False):  # type: ignore
    id: int
