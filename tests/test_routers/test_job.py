from datetime import datetime, timedelta, timezone
from random import choice

import pytest

from sqlmodel import Session, select
from starlette import status
from starlette.testclient import TestClient

from app.handlers.job import JobHandler
from app.job_scrapers.scraper import RemoteStatus, Source
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


def test_get_job(client: TestClient, job: JobRead, db_session: Session):
    url = f"/{JOB_INTERFACE}/{job.id}"
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK


def test_list_jobs(client: TestClient, job: JobRead, db_session: Session):
    url = f"/{JOB_INTERFACE}/?country={job.country}"
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert job.listing_remote

    url = f"/{JOB_INTERFACE}/?listing_remote={job.listing_remote.value}"
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1


def test_list_jobs_filters(client: TestClient, db_session: Session):

    handler = JobHandler(db_session)
    now = datetime.utcnow()
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

    response = client.get(f"/{JOB_INTERFACE}/", params={"company": "acme"})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2

    response = client.get(
        f"/{JOB_INTERFACE}/",
        params={"company": "acme", "analysed": False},
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "alpha"

    min_created_at = min(row.created_at for row in created_rows)
    max_created_at = max(row.created_at for row in created_rows)
    response = client.get(
        f"/{JOB_INTERFACE}/",
        params={
            "created_at_gte": min_created_at.isoformat(),
            "created_at_lte": max_created_at.isoformat(),
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 3

    response = client.get(
        f"/{JOB_INTERFACE}/",
        params={
            "listing_date_gte": older.date().isoformat(),
            "listing_date_lte": now.date().isoformat(),
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2


def test_job_summary(client: TestClient, db_session: Session):
    handler = JobHandler(db_session)
    now = datetime.now(timezone.utc)

    jobs = [
        JobCreate(
            title="recent",
            company="acme",
            source_url="https://example.com/recent",
            country="Sweden",
            listing_remote=RemoteStatus.REMOTE,
            applied=False,
            positive_keyword_match=True,
            source=Source.LINKEDIN,
            created_at=now,
        ),
        JobCreate(
            title="old",
            company="globex",
            source_url="https://example.com/old",
            country="DE",
            listing_remote=RemoteStatus.ONSITE,
            applied=True,
            source=Source.TEAMTAILOR,
            created_at=now - timedelta(days=10),
        ),
    ]
    for job in jobs:
        handler.save(Job.model_validate(job))
    db_session.commit()

    response = client.get(f"/{JOB_INTERFACE}/summary")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["counts_by_source"]["linkedin"] == 1
    assert data["counts_by_source"]["teamtailor"] == 1
    assert data["counts_by_country"]["Sweden"] == 1
    assert data["counts_by_country"]["DE"] == 1
    assert data["counts_by_remote_status"]["REMOTE"] == 1
    assert data["counts_by_remote_status"]["ONSITE"] == 1
    assert data["to_review"] == 1
    assert data["eu_remote"] == 1
    assert data["sweden"] == 1
    assert data["new7d"] == 1
    assert data["positive_matches"] == 1
