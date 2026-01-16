from datetime import datetime, timedelta, timezone
from random import choice

import pytest

from sqlmodel import Session, select
from starlette import status
from starlette.testclient import TestClient

from app.handlers.job import JobHandler
from app.job_scrapers.scraper import RemoteStatus
from app.models.job import Job, JobCreate, JobRead
from app.routers.job import INTERFACE as JOB_INTERFACE


@pytest.fixture
def job(db_session: Session) -> JobRead:
    job_data = JobCreate(
        title="test title",
        company="test company",
        source_url="test linkedin url",
        listing_remote=choice(list(RemoteStatus)),
        country="test country",
    )

    handler = JobHandler(db_session)
    handler.save(Job.model_validate(job_data))
    db_session.commit()

    job_instance = db_session.exec(
        select(Job).where(Job.source_url == job_data.source_url)
    ).first()
    assert job_instance is not None
    return JobRead.model_validate(job_instance)


def test_get_job(authed_client: TestClient, job: JobRead, db_session: Session):
    url = f"/{JOB_INTERFACE}/{job.id}"
    response = authed_client.get(url)

    assert response.status_code == status.HTTP_200_OK


def test_list_jobs(authed_client: TestClient, job: JobRead, db_session: Session):
    url = f"/{JOB_INTERFACE}/?country={job.country}"
    response = authed_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert job.listing_remote

    url = f"/{JOB_INTERFACE}/?listing_remote={job.listing_remote.value}"
    response = authed_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1


def test_list_jobs_filters(authed_client: TestClient, db_session: Session):

    handler = JobHandler(db_session)
    now = datetime.now(timezone.utc)
    older = now - timedelta(days=5)

    jobs = [
        JobCreate(
            title="alpha",
            company="acme",
            source_url="https://example.com/a",
            country="SE",
            analysed=False,
            created_at=older,
            listing_date=older.date(),
        ),
        JobCreate(
            title="beta",
            company="acme",
            source_url="https://example.com/b",
            country="SE",
            analysed=True,
            created_at=now,
            listing_date=now.date(),
        ),
        JobCreate(
            title="gamma",
            company="globex",
            source_url="https://example.com/c",
            country="DE",
            analysed=False,
            created_at=now,
            listing_date=None,
        ),
    ]
    for job in jobs:
        handler.save(Job.model_validate(job))
    db_session.commit()
    created_rows = db_session.exec(select(Job)).all()
    assert created_rows

    response = authed_client.get(f"/{JOB_INTERFACE}/", params={"company": "acme"})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2

    response = authed_client.get(
        f"/{JOB_INTERFACE}/",
        params={"company": "acme", "analysed": False},
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "alpha"

    min_created_at = min(row.created_at for row in created_rows)
    max_created_at = max(row.created_at for row in created_rows)
    response = authed_client.get(
        f"/{JOB_INTERFACE}/",
        params={
            "created_at_gte": min_created_at.isoformat(),
            "created_at_lte": max_created_at.isoformat(),
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 3

    response = authed_client.get(
        f"/{JOB_INTERFACE}/",
        params={
            "listing_date_gte": older.date().isoformat(),
            "listing_date_lte": now.date().isoformat(),
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2


def test_job_routes_require_user_header(client: TestClient):
    response = client.get(f"/{JOB_INTERFACE}/")
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_job_routes_reject_invalid_user(client: TestClient):
    response = client.get(f"/{JOB_INTERFACE}/", headers={"X-User-Id": "999999"})
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_job_routes_accept_valid_user(authed_client: TestClient):
    response = authed_client.get(f"/{JOB_INTERFACE}/")
    assert response.status_code == status.HTTP_200_OK
