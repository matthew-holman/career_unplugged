from sqlmodel import Session
from starlette import status
from starlette.testclient import TestClient

from app.handlers.job import JobHandler
from app.models.job import JobCreate
from app.routers.job import INTERFACE as JOB_INTERFACE


def test_get_job(client: TestClient, db_session: Session):
    job = JobCreate(
        title="test title",
        company="test company",
        location="test location",
        linkedin_url="test linkedin url",
    )

    job = JobHandler(db_session).create(job=job)
    url = f"/{JOB_INTERFACE}/{job.id}"
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
