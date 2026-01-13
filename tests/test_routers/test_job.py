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
    jobs = [
        JobCreate(
            title="alpha",
            company="acme",
            source_url="https://example.com/a",
            country="SE",
            analysed=False,
        ),
        JobCreate(
            title="beta",
            company="acme",
            source_url="https://example.com/b",
            country="SE",
            analysed=True,
        ),
        JobCreate(
            title="gamma",
            company="globex",
            source_url="https://example.com/c",
            country="DE",
            analysed=False,
        ),
    ]
    for job in jobs:
        handler.save(Job.model_validate(job))
    db_session.commit()

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
