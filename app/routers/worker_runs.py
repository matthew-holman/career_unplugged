from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.auth.current_user import get_current_user
from app.db.db import get_db
from app.handlers.worker_run import WorkerRunHandler
from app.models.worker_run import WorkerRunStatus
from app.schemas.worker_run import WorkerRunFilter, WorkerRunRead

router = APIRouter(
    prefix="/worker-runs",
    tags=["WorkerRuns"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/{worker_run_id}", response_model=WorkerRunRead)
def get_worker_run(
    worker_run_id: int,
    db_session: Session = Depends(get_db),
) -> WorkerRunRead:
    handler = WorkerRunHandler(db_session)
    run = handler.get_by_id(worker_run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return WorkerRunRead.model_validate(run)


@router.get("", response_model=list[WorkerRunRead])
def list_worker_runs(
    filters: Annotated[WorkerRunFilter, Query()],
    db_session: Session = Depends(get_db),
) -> list[WorkerRunRead]:
    handler = WorkerRunHandler(db_session)
    status_value = None
    if filters.status:
        try:
            status_value = WorkerRunStatus(filters.status)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST) from exc
    runs = handler.list(
        status=status_value,
        worker_name=filters.worker_name,
        started_at_gte=filters.started_at_gte,
        started_at_lte=filters.started_at_lte,
    )
    return [WorkerRunRead.model_validate(run) for run in runs]
