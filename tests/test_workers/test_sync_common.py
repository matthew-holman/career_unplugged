from sqlmodel import Session, select

from app.handlers.job import JobHandler
from app.job_scrapers.scraper import (
    JobPost,
    JobResponse,
    Location,
    RemoteStatus,
    Source,
)
from app.models.job import Job
from app.workers.sync_common import build_jobs_to_save, should_save_job

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_linkedin_job_post(job_url: str) -> JobPost:
    return JobPost(
        title="Engineering Manager",  # must match a value in JOB_TITLES
        company_name="Acme",
        job_url=job_url,
        location=Location(country="Germany"),
        remote_status=RemoteStatus.ONSITE,
        source=Source.LINKEDIN,
    )


def _make_ats_job_post(job_url: str, source: Source = Source.ASHBY) -> JobPost:
    return JobPost(
        title="Engineering Manager",
        company_name="Acme",
        job_url=job_url,
        location=Location(country="Germany"),
        remote_status=RemoteStatus.ONSITE,
        source=source,
    )


# ---------------------------------------------------------------------------
# Unit tests — no database required
# ---------------------------------------------------------------------------


def test_build_jobs_to_save_routes_linkedin_url_to_linkedin_source_url() -> None:
    url = "https://www.linkedin.com/jobs/view/123"
    jobs = build_jobs_to_save(JobResponse(jobs=[_make_linkedin_job_post(url)]))
    assert len(jobs) == 1
    assert jobs[0].linkedin_source_url == url
    assert jobs[0].ats_source_url is None


def test_build_jobs_to_save_routes_ats_url_to_ats_source_url() -> None:
    url = "https://jobs.ashbyhq.com/acme/456"
    jobs = build_jobs_to_save(JobResponse(jobs=[_make_ats_job_post(url)]))
    assert len(jobs) == 1
    assert jobs[0].ats_source_url == url
    assert jobs[0].linkedin_source_url is None


# ---------------------------------------------------------------------------
# should_save_job — preferred location bypass tests
# ---------------------------------------------------------------------------


def _make_unmatched_title_job_post(
    city: str | None = None, country: str | None = None, company: str = "Acme"
) -> JobPost:
    return JobPost(
        title="Product Manager",  # does NOT match any value in JOB_TITLES
        company_name=company,
        job_url="https://example.com/job/1",
        location=Location(city=city, country=country),
        remote_status=RemoteStatus.ONSITE,
        source=Source.ASHBY,
    )


def test_preferred_city_saves_job_without_title_match() -> None:
    job = _make_unmatched_title_job_post(city="Göteborg", country="Sweden")
    assert should_save_job(job) is True


def test_preferred_country_saves_job_without_title_match() -> None:
    job = _make_unmatched_title_job_post(city="Alingsås", country="Sweden")
    assert should_save_job(job) is True


def test_non_preferred_location_does_not_bypass_title_check() -> None:
    job = _make_unmatched_title_job_post(city="Amsterdam", country="Netherlands")
    assert should_save_job(job) is False


def test_preferred_location_still_respects_company_ignore() -> None:
    job = _make_unmatched_title_job_post(
        city="Berlin", country="Germany", company="Canonical"
    )
    assert should_save_job(job) is False


# ---------------------------------------------------------------------------
# DB integration tests — verify actual insert succeeds
# ---------------------------------------------------------------------------


def test_linkedin_job_saves_with_linkedin_source_url(db_session: Session) -> None:
    job = Job(
        title="Engineering Manager",
        company="Acme",
        source=Source.LINKEDIN,
        linkedin_source_url="https://www.linkedin.com/jobs/view/123",
    )
    handler = JobHandler(db_session)
    handler.save(job)
    db_session.commit()

    saved = db_session.exec(select(Job)).first()
    assert saved is not None
    assert saved.linkedin_source_url == "https://www.linkedin.com/jobs/view/123"
    assert saved.ats_source_url is None


def test_ats_job_saves_with_ats_source_url(db_session: Session) -> None:
    job = Job(
        title="Engineering Manager",
        company="Acme",
        source=Source.ASHBY,
        ats_source_url="https://jobs.ashbyhq.com/acme/456",
    )
    handler = JobHandler(db_session)
    handler.save(job)
    db_session.commit()

    saved = db_session.exec(select(Job)).first()
    assert saved is not None
    assert saved.ats_source_url == "https://jobs.ashbyhq.com/acme/456"
    assert saved.linkedin_source_url is None
