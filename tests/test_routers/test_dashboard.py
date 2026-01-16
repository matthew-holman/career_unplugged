from sqlmodel import Session
from starlette import status
from starlette.testclient import TestClient

from app.handlers.job import JobHandler
from app.job_scrapers.scraper import RemoteStatus, Source
from app.models.job import Job, JobCreate


def test_dashboard_jobs_summary(client: TestClient, db_session: Session):
    handler = JobHandler(db_session)

    jobs = [
        JobCreate(
            title="recent",
            company="acme",
            source_url="https://example.com/recent",
            country="Sweden",
            listing_remote=RemoteStatus.REMOTE,
            positive_keyword_match=True,
            source=Source.LINKEDIN,
        ),
        JobCreate(
            title="old",
            company="globex",
            source_url="https://example.com/old",
            country="DE",
            listing_remote=RemoteStatus.ONSITE,
            source=Source.TEAMTAILOR,
        ),
    ]
    for job in jobs:
        handler.save(Job.model_validate(job))
    db_session.commit()

    response = client.get("/dashboard/jobs/summary")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["counts_by_source"]["linkedin"] == 1
    assert data["counts_by_source"]["teamtailor"] == 1
    assert data["counts_by_country"]["Sweden"] == 1
    assert data["counts_by_country"]["DE"] == 1
    assert data["counts_by_remote_status"]["REMOTE"] == 1
    assert data["counts_by_remote_status"]["ONSITE"] == 1
    assert data["to_review"] == 2
    assert data["eu_remote"] == 1
    assert data["sweden"] == 1
    assert data["new7d"] == 2
    assert data["positive_matches"] == 1
