from sqlmodel import Session, select
from starlette import status
from starlette.testclient import TestClient

from app.handlers.job import JobHandler
from app.job_scrapers.scraper import RemoteStatus, Source
from app.models.job import Job, JobCreate
from app.models.user import User
from app.models.user_job import UserJob


def test_dashboard_jobs_summary(
    authed_client: TestClient, db_session: Session, test_user: User
):
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
    created_jobs = db_session.exec(select(Job)).all()
    assert created_jobs
    db_session.add(
        UserJob(
            user_id=test_user.id,
            job_id=created_jobs[0].id,
            applied=True,
            ignored=False,
        )
    )
    db_session.commit()

    response = authed_client.get("/dashboard/jobs/summary")
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
    assert data["new7d"] == 2
    assert data["positive_matches"] == 1
