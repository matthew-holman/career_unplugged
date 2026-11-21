import pytest

from app.handlers.job import JobHandler
from app.models.job import Job, JobCreate


@pytest.fixture
def job_create() -> JobCreate:
    return JobCreate(
        title="test title",
        company="test company",
        ats_source_url="https://example.com/job/1",
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


def test_eu_remote_filter_excludes_remote_listings_in_other_countries(
    db_session, test_user
):
    """REMOTE in Germany is not eligible from Sweden unless analysis says so."""
    from app.filters.job import JobFilter
    from app.job_scrapers.scraper import RemoteStatus

    def _job(title: str, country: str, true_remote: bool) -> Job:
        return Job.model_validate(
            JobCreate(
                title=title,
                company="acme",
                ats_source_url=f"https://example.com/{title}",
                country=country,
                listing_remote=RemoteStatus.REMOTE,
                true_remote=true_remote,
            )
        )

    handler = JobHandler(db_session)
    handler.save_all(
        [
            _job("germany-unanalysed", "Germany", False),
            _job("germany-eu-wide", "Germany", True),
            _job("sweden-unanalysed", "Sweden", False),
        ]
    )
    db_session.commit()

    results = handler.list_for_user(JobFilter(eu_remote=True), test_user.id)

    assert {job.title for job in results} == {"germany-eu-wide", "sweden-unanalysed"}
