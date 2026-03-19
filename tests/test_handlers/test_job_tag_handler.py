import pytest

from app.handlers.job_tag import JobTagHandler
from app.models.job import Job
from app.models.job_tag import JobTag, TagCategory


@pytest.fixture
def saved_job(db_session) -> Job:
    job = Job(
        title="Engineering Manager",
        company="Acme",
        ats_source_url="https://example.com/job/1",
        country="Sweden",
    )
    db_session.add(job)
    db_session.flush()
    return job


def test_replace_tags_flushes_but_does_not_commit(db_session, saved_job, monkeypatch):
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

    handler = JobTagHandler(db_session)
    tags = [JobTag(job_id=saved_job.id, name="Python", category=TagCategory.TECH_STACK)]
    handler.replace_tags(saved_job.id, tags)

    assert committed is False
    assert flushed is True


def test_replace_tags_sets_tags_for_job(db_session, saved_job):
    handler = JobTagHandler(db_session)
    tags = [
        JobTag(job_id=saved_job.id, name="Python", category=TagCategory.TECH_STACK),
        JobTag(
            job_id=saved_job.id,
            name="Engineering Manager",
            category=TagCategory.ROLE_TYPE,
        ),
    ]
    handler.replace_tags(saved_job.id, tags)

    result = handler.get_tags_for_jobs([saved_job.id])
    assert len(result) == 2
    names = {t.name for t in result}
    assert names == {"Python", "Engineering Manager"}


def test_replace_tags_replaces_not_accumulates(db_session, saved_job):
    handler = JobTagHandler(db_session)

    first_tags = [
        JobTag(job_id=saved_job.id, name="Python", category=TagCategory.TECH_STACK)
    ]
    handler.replace_tags(saved_job.id, first_tags)

    second_tags = [
        JobTag(job_id=saved_job.id, name="FastAPI", category=TagCategory.TECH_STACK)
    ]
    handler.replace_tags(saved_job.id, second_tags)

    result = handler.get_tags_for_jobs([saved_job.id])
    assert len(result) == 1
    assert result[0].name == "FastAPI"


def test_replace_tags_with_empty_list_clears_tags(db_session, saved_job):
    handler = JobTagHandler(db_session)

    tags = [JobTag(job_id=saved_job.id, name="Python", category=TagCategory.TECH_STACK)]
    handler.replace_tags(saved_job.id, tags)
    handler.replace_tags(saved_job.id, [])

    result = handler.get_tags_for_jobs([saved_job.id])
    assert result == []


def test_get_tags_for_jobs_batch_loads_multiple_jobs(db_session, saved_job):
    second_job = Job(
        title="Staff Engineer",
        company="Acme",
        ats_source_url="https://example.com/job/2",
        country="Germany",
    )
    db_session.add(second_job)
    db_session.flush()

    tag_handler = JobTagHandler(db_session)
    tag_handler.replace_tags(
        saved_job.id,
        [JobTag(job_id=saved_job.id, name="Python", category=TagCategory.TECH_STACK)],
    )
    tag_handler.replace_tags(
        second_job.id,
        [JobTag(job_id=second_job.id, name="Docker", category=TagCategory.TECH_STACK)],
    )

    result = tag_handler.get_tags_for_jobs([saved_job.id, second_job.id])
    assert len(result) == 2
    job_ids = {t.job_id for t in result}
    assert job_ids == {saved_job.id, second_job.id}


def test_get_tags_for_jobs_returns_empty_for_no_ids(db_session):
    handler = JobTagHandler(db_session)
    result = handler.get_tags_for_jobs([])
    assert result == []
