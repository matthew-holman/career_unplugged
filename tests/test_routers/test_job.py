from random import choice

import pytest

from sqlmodel import Session
from starlette import status
from starlette.testclient import TestClient

from app.handlers.job import JobHandler
from app.job_scrapers.scraper import RemoteStatus
from app.models.job import JobCreate, JobRead
from app.routers.job import INTERFACE as JOB_INTERFACE


@pytest.fixture
def job(db_session: Session) -> JobRead:
    job_data = JobCreate(
        title="test title",
        company="test company",
        location="test location",
        linkedin_url="test linkedin url",
        listing_remote=choice(list(RemoteStatus)),
        country="test country",
    )

    job_instance = JobHandler(db_session).create(job=job_data)
    return job_instance


def test_get_job(client: TestClient, job: JobRead, db_session: Session):
    url = f"/{JOB_INTERFACE}/{job.id}"
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK


def test_list_jobs(client: TestClient, job: JobRead, db_session: Session):
    url = f"/{JOB_INTERFACE}/?country={job.country}"
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1

    url = f"/{JOB_INTERFACE}/?listing_remote={job.listing_remote.value}"
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
