from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlmodel import Session

from app.auth.current_user import get_current_user
from app.db.db import get_db
from app.handlers.worker_run import WorkerRunHandler
from app.schemas.sync import AtsSyncRequest, LinkedinSyncRequest, SyncAllRequest
from app.schemas.worker_run import WorkerRunRead
from app.workers.sync_tasks import (
    run_ats_sync_background,
    run_linkedin_sync_background,
)

router = APIRouter(
    prefix="/sync",
    tags=["Sync"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/ats", response_model=WorkerRunRead)
def sync_ats(
    payload: AtsSyncRequest,
    background_tasks: BackgroundTasks,
    db_session: Session = Depends(get_db),
) -> WorkerRunRead:
    handler = WorkerRunHandler(db_session)
    run = handler.create_run("sync_ats")
    db_session.commit()
    background_tasks.add_task(
        run_ats_sync_background, worker_run_id=run.id, request=payload
    )
    return WorkerRunRead.model_validate(run)


@router.post("/linkedin", response_model=WorkerRunRead)
def sync_linkedin(
    payload: LinkedinSyncRequest,
    background_tasks: BackgroundTasks,
    db_session: Session = Depends(get_db),
) -> WorkerRunRead:
    handler = WorkerRunHandler(db_session)
    run = handler.create_run("sync_linkedin")
    db_session.commit()
    background_tasks.add_task(
        run_linkedin_sync_background, worker_run_id=run.id, request=payload
    )
    return WorkerRunRead.model_validate(run)


@router.post("/all", response_model=WorkerRunRead)
def sync_all(
    payload: SyncAllRequest,
    background_tasks: BackgroundTasks,
    db_session: Session = Depends(get_db),
) -> WorkerRunRead:
    handler = WorkerRunHandler(db_session)
    run = handler.create_run("sync_all")
    db_session.commit()
    background_tasks.add_task(
        run_ats_sync_background, worker_run_id=run.id, request=payload
    )
    background_tasks.add_task(
        run_linkedin_sync_background,
        worker_run_id=run.id,
        request=LinkedinSyncRequest(),
    )
    return WorkerRunRead.model_validate(run)
