from urllib.parse import quote

from sqlmodel import Session, col, select

from app.handlers.career_page import CareerPageHandler
from app.handlers.job import JobHandler
from app.job_scrapers.scraper import RemoteStatus, Source
from app.models.job import Job
from app.models.user import User
from app.models.user_job import UserJob
from app.workers import job_analyser


class _FakeResponse:
    __slots__ = ("text", "status_code")

    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code


class _FakeSession:
    __slots__ = ("_response",)

    def __init__(self, response: _FakeResponse) -> None:
        self._response = response

    def get(self, url: str) -> _FakeResponse:
        return self._response


def _make_linkedin_html(external_url: str) -> str:
    """Build minimal LinkedIn job page HTML embedding the given external apply URL."""
    encoded = quote(external_url, safe="")
    linkedin_url = (
        "https://www.linkedin.com/jobs/view/externalApply/?"
        f"url={encoded}&tracking=foo"
    )
    return (
        "<html><body>"
        '<code id="applyUrl" style="display:none">'
        f'<!--"{linkedin_url}"-->'
        "</code>"
        '<section class="core-section-container my-3 description">'
        "Role details"
        "</section>"
        "</body></html>"
    )


def test_analyser_discovers_career_page_from_linkedin(db_session: Session) -> None:
    external_url = "https://jobs.ashbyhq.com/acme/123"
    html = _make_linkedin_html(external_url)

    job = Job(
        title="Data Engineer",
        company="Acme",
        source=Source.LINKEDIN,
        linkedin_source_url="https://www.linkedin.com/jobs/view/123",
        listing_remote=RemoteStatus.UNKNOWN,
    )
    db_session.add(job)
    db_session.commit()

    career_handler = CareerPageHandler(db_session)
    job_handler = JobHandler(db_session)
    session = _FakeSession(_FakeResponse(html))

    job_analyser._apply_description_analysis(job, session, career_handler, job_handler)

    page = career_handler.get_by_url("https://jobs.ashbyhq.com/acme")
    assert page is not None
    assert page.company_name == "acme"


def test_analyser_sets_ats_source_url_on_linkedin_job_when_no_conflict(
    db_session: Session,
) -> None:
    """When no ATS job already exists for the external URL, set ats_source_url in place."""
    external_url = "https://jobs.ashbyhq.com/acme/456"
    html = _make_linkedin_html(external_url)

    job = Job(
        title="Data Engineer",
        company="Acme",
        source=Source.LINKEDIN,
        linkedin_source_url="https://www.linkedin.com/jobs/view/456",
        listing_remote=RemoteStatus.UNKNOWN,
    )
    db_session.add(job)
    db_session.commit()

    career_handler = CareerPageHandler(db_session)
    job_handler = JobHandler(db_session)
    session = _FakeSession(_FakeResponse(html))

    job_analyser._apply_description_analysis(job, session, career_handler, job_handler)

    assert job.ats_source_url == external_url
    assert job.deleted_at is None


def test_analyser_merges_linkedin_job_into_existing_ats_job(
    db_session: Session, test_user: User
) -> None:
    """When an ATS job with the same URL already exists, merge and soft-delete the LinkedIn job."""
    external_url = "https://jobs.ashbyhq.com/acme/789"
    html = _make_linkedin_html(external_url)

    ats_job = Job(
        title="Data Engineer",
        company="Acme",
        source=Source.ASHBY,
        ats_source_url=external_url,
        listing_remote=RemoteStatus.UNKNOWN,
    )
    linkedin_job = Job(
        title="Data Engineer",
        company="Acme",
        source=Source.LINKEDIN,
        linkedin_source_url="https://www.linkedin.com/jobs/view/789",
        listing_remote=RemoteStatus.UNKNOWN,
    )
    db_session.add_all([ats_job, linkedin_job])
    db_session.commit()

    # Mark the LinkedIn job as applied by test_user
    db_session.add(
        UserJob(
            user_id=test_user.id,
            job_id=linkedin_job.id,
            applied=True,
            ignored=False,
        )
    )
    db_session.commit()

    career_handler = CareerPageHandler(db_session)
    job_handler = JobHandler(db_session)
    session = _FakeSession(_FakeResponse(html))

    job_analyser._apply_description_analysis(
        linkedin_job, session, career_handler, job_handler
    )

    db_session.refresh(ats_job)
    db_session.refresh(linkedin_job)

    # LinkedIn job must be soft-deleted
    assert linkedin_job.deleted_at is not None

    # ATS job inherits the LinkedIn source URL
    assert ats_job.linkedin_source_url == "https://www.linkedin.com/jobs/view/789"

    # UserJob activity transferred to the ATS job
    transferred = db_session.exec(
        select(UserJob)
        .where(col(UserJob.user_id) == test_user.id)
        .where(col(UserJob.job_id) == ats_job.id)
    ).first()
    assert transferred is not None
    assert transferred.applied is True
