from __future__ import annotations

from datetime import datetime, timezone

from app.db.db import get_db
from app.handlers.worker_run import WorkerRunHandler
from app.log import Log
from app.schemas.sync import AtsSyncRequest, LinkedinSyncRequest
from app.workers.sync_ats import run_sync_ats_with_session
from app.workers.sync_linkedin import run_sync_linkedin_with_session


def run_ats_sync_background(*, worker_run_id: int, request: AtsSyncRequest) -> None:
    Log.setup(application_name="sync_ats_background")
    with next(get_db()) as db_session:
        handler = WorkerRunHandler(db_session)
        run = handler.get_by_id(worker_run_id)
        if not run:
            return
        try:
            summary = run_sync_ats_with_session(
                db_session,
                career_page_ids=request.career_page_ids,
                max_age_hours=request.max_age_hours,
                include_inactive=request.include_inactive,
            )
            handler.mark_succeeded(run, summary)
        except Exception as exc:
            handler.mark_failed(run, [str(exc)], summary=None)
        run.finished_at = datetime.now(timezone.utc)
        db_session.commit()


def run_linkedin_sync_background(
    *, worker_run_id: int, request: LinkedinSyncRequest
) -> None:
    Log.setup(application_name="sync_linkedin_background")
    with next(get_db()) as db_session:
        handler = WorkerRunHandler(db_session)
        run = handler.get_by_id(worker_run_id)
        if not run:
            return
        try:
            summary = run_sync_linkedin_with_session(db_session)
            handler.mark_succeeded(run, summary)
        except Exception as exc:
            handler.mark_failed(run, [str(exc)], summary=None)
        run.finished_at = datetime.now(timezone.utc)
        db_session.commit()
