from sqlmodel import Session, select
from starlette import status
from starlette.testclient import TestClient

from app.handlers.job import JobHandler
from app.models.job import Job, JobCreate
from app.models.user import User
from app.models.user_job import UserJob


def _seed_activity_jobs(db_session: Session, test_user: User) -> None:
    handler = JobHandler(db_session)
    jobs = [
        JobCreate(
            title="applied",
            company="acme",
            source_url="https://example.com/applied",
            country="SE",
        ),
        JobCreate(
            title="ignored",
            company="acme",
            source_url="https://example.com/ignored",
            country="SE",
        ),
        JobCreate(
            title="neither",
            company="acme",
            source_url="https://example.com/neither",
            country="SE",
        ),
    ]
    for job in jobs:
        handler.save(Job.model_validate(job))
    db_session.commit()

    created_jobs = db_session.exec(select(Job)).all()
    job_map = {job.title: job for job in created_jobs}
    db_session.add_all(
        [
            UserJob(
                user_id=test_user.id,
                job_id=job_map["applied"].id,
                applied=True,
                ignored=False,
            ),
            UserJob(
                user_id=test_user.id,
                job_id=job_map["ignored"].id,
                applied=False,
                ignored=True,
            ),
            UserJob(
                user_id=test_user.id,
                job_id=job_map["neither"].id,
                applied=False,
                ignored=False,
            ),
        ]
    )
    db_session.commit()


def test_user_activity_filters(
    authed_client: TestClient, db_session: Session, test_user: User
) -> None:
    _seed_activity_jobs(db_session, test_user)

    response = authed_client.get("/user/activity")
    assert response.status_code == status.HTTP_200_OK
    titles = {item["title"] for item in response.json()}
    assert titles == {"applied", "ignored"}

    response = authed_client.get("/user/activity", params={"activity": "applied"})
    assert response.status_code == status.HTTP_200_OK
    titles = {item["title"] for item in response.json()}
    assert titles == {"applied"}

    response = authed_client.get("/user/activity", params={"activity": "ignored"})
    assert response.status_code == status.HTTP_200_OK
    titles = {item["title"] for item in response.json()}
    assert titles == {"ignored"}

    response = authed_client.get("/user/activity", params={"activity": "both"})
    assert response.status_code == status.HTTP_200_OK
    titles = {item["title"] for item in response.json()}
    assert titles == {"applied", "ignored"}

    response = authed_client.get("/user/activity", params={"applied": True})
    assert response.status_code == status.HTTP_200_OK
    titles = {item["title"] for item in response.json()}
    assert titles == {"applied"}

    response = authed_client.get("/user/activity", params={"ignored": True})
    assert response.status_code == status.HTTP_200_OK
    titles = {item["title"] for item in response.json()}
    assert titles == {"ignored"}
