from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models.worker_run import WorkerRun, WorkerRunStatus


@dataclass
class WorkerRunHandler:
    db_session: Session

    def create_run(self, worker_name: str) -> WorkerRun:
        run = WorkerRun(
            worker_name=worker_name,
            status=WorkerRunStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        self.db_session.add(run)
        self.db_session.flush()
        return run

    def mark_succeeded(self, worker_run: WorkerRun, summary: dict) -> None:
        worker_run.status = WorkerRunStatus.SUCCEEDED
        worker_run.summary = summary
        worker_run.errors = []
        self.db_session.add(worker_run)

    def mark_failed(
        self, worker_run: WorkerRun, errors: list[str], summary: dict | None = None
    ) -> None:
        worker_run.status = WorkerRunStatus.FAILED
        worker_run.errors = errors
        worker_run.summary = summary
        self.db_session.add(worker_run)

    def get_by_id(self, worker_run_id: int) -> WorkerRun | None:
        statement = select(WorkerRun).where(WorkerRun.id == worker_run_id)
        return self.db_session.exec(statement).first()

    def list(
        self,
        *,
        status: WorkerRunStatus | None = None,
        worker_name: str | None = None,
        started_at_gte: datetime | None = None,
        started_at_lte: datetime | None = None,
    ) -> list[WorkerRun]:
        query = select(WorkerRun)
        if status is not None:
            query = query.where(WorkerRun.status == status)
        if worker_name is not None:
            query = query.where(WorkerRun.worker_name == worker_name)
        if started_at_gte is not None:
            query = query.where(WorkerRun.started_at >= started_at_gte)
        if started_at_lte is not None:
            query = query.where(WorkerRun.started_at <= started_at_lte)
        query = query.order_by(WorkerRun.started_at.desc())  # type: ignore[attr-defined]
        return self.db_session.exec(query).all()
