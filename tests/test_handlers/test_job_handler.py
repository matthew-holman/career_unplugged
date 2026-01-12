import pytest

from app.handlers.job import JobHandler
from app.models.job import Job, JobCreate


@pytest.fixture
def job_create() -> JobCreate:
    return JobCreate(
        title="test title",
        company="test company",
        source_url="https://example.com/job/1",
        country="test country",
    )


def test_job_handler_save_all_does_not_commit(db_session, monkeypatch, job_create):
    committed = False
    flushed = False
    original_flush = db_session.flush

    def fake_commit():
        nonlocal committed
        committed = True

    def fake_flush(*args, **kwargs):
        nonlocal flushed
        flushed = True
        return original_flush(*args, **kwargs)

    monkeypatch.setattr(db_session, "commit", fake_commit)
    monkeypatch.setattr(db_session, "flush", fake_flush)

    handler = JobHandler(db_session)
    job = Job.model_validate(job_create)
    handler.save_all([job])

    assert committed is False
    assert flushed is True
