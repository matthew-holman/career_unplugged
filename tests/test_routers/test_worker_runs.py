from datetime import datetime, timezone

from sqlmodel import Session
from starlette import status
from starlette.testclient import TestClient

from app.models.worker_run import WorkerRun, WorkerRunStatus


def test_get_worker_run(authed_client: TestClient, db_session: Session) -> None:
    run = WorkerRun(
        worker_name="sync_ats",
        status=WorkerRunStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    response = authed_client.get(f"/worker-runs/{run.id}")
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["id"] == run.id
    assert payload["worker_name"] == "sync_ats"


def test_list_worker_runs_filters(
    authed_client: TestClient, db_session: Session
) -> None:
    now = datetime.now(timezone.utc)
    runs = [
        WorkerRun(
            worker_name="sync_ats",
            status=WorkerRunStatus.RUNNING,
            started_at=now,
        ),
        WorkerRun(
            worker_name="sync_linkedin",
            status=WorkerRunStatus.FAILED,
            started_at=now,
        ),
    ]
    for run in runs:
        db_session.add(run)
    db_session.commit()

    response = authed_client.get("/worker-runs", params={"worker_name": "sync_ats"})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1

    response = authed_client.get("/worker-runs", params={"status": "FAILED"})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
