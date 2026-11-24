from sqlmodel import Session, select
from starlette import status
from starlette.testclient import TestClient

import app.routers.sync as sync_router
import app.workers.sync_tasks as sync_tasks

from app.handlers.worker_run import WorkerRunHandler
from app.models.worker_run import WorkerRun, WorkerRunStatus
from app.schemas.sync import AtsSyncRequest


def test_sync_ats_endpoint_enqueues_run(
    authed_client: TestClient, db_session: Session, monkeypatch
) -> None:
    # TestClient runs background tasks inline, so without this stub the test
    # performs a real, networked ATS sync against the dev database.
    queued: list[dict[str, object]] = []

    def fake_run_ats_sync_background(**kwargs: object) -> None:
        queued.append(kwargs)

    monkeypatch.setattr(
        sync_router, "run_ats_sync_background", fake_run_ats_sync_background
    )

    response = authed_client.post("/sync/ats", json={})
    assert response.status_code == status.HTTP_200_OK
    assert len(queued) == 1

    payload = response.json()
    assert payload["worker_name"] == "sync_ats"
    assert payload["status"] == WorkerRunStatus.RUNNING.value
    assert payload["run_id"]

    run = db_session.exec(
        select(WorkerRun).where(WorkerRun.run_id == payload["run_id"])
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
