from sqlmodel import Session, select
from starlette import status
from starlette.testclient import TestClient

import app.workers.sync_tasks as sync_tasks

from app.handlers.worker_run import WorkerRunHandler
from app.models.worker_run import WorkerRun, WorkerRunStatus
from app.schemas.sync import AtsSyncRequest


def test_sync_ats_endpoint_enqueues_run(
    authed_client: TestClient, db_session: Session
) -> None:
    response = authed_client.post("/sync/ats", json={})
    assert response.status_code == status.HTTP_200_OK

    payload = response.json()
    assert payload["worker_name"] == "sync_ats"
    assert payload["status"] == WorkerRunStatus.RUNNING.value
    assert payload["id"]

    run = db_session.exec(
        select(WorkerRun).where(WorkerRun.id == payload["id"])
    ).first()
    assert run is not None


def test_sync_ats_background_success(db_session: Session, monkeypatch) -> None:
    handler = WorkerRunHandler(db_session)
    run = handler.create_run("sync_ats")
    db_session.commit()

    def fake_run_sync_ats_with_session(*args, **kwargs):
        return {"pages_selected": 2}

    monkeypatch.setattr(
        sync_tasks, "run_sync_ats_with_session", fake_run_sync_ats_with_session
    )

    sync_tasks.run_ats_sync_background(worker_run_id=run.id, request=AtsSyncRequest())

    db_session.refresh(run)
    assert run.status == WorkerRunStatus.SUCCEEDED
    assert run.finished_at is not None
    assert run.summary is not None
    assert run.summary["pages_selected"] == 2


def test_sync_ats_background_failure(db_session: Session, monkeypatch) -> None:
    handler = WorkerRunHandler(db_session)
    run = handler.create_run("sync_ats")
    db_session.commit()

    def fake_run_sync_ats_with_session(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        sync_tasks, "run_sync_ats_with_session", fake_run_sync_ats_with_session
    )

    sync_tasks.run_ats_sync_background(worker_run_id=run.id, request=AtsSyncRequest())

    db_session.refresh(run)
    assert run.status == WorkerRunStatus.FAILED
    assert run.finished_at is not None
    assert run.errors
