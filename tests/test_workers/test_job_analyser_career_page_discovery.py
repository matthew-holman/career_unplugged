from urllib.parse import quote

from app.handlers.career_page import CareerPageHandler
from app.job_scrapers.scraper import RemoteStatus, Source
from app.models.job import Job
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


def test_analyser_discovers_career_page_from_linkedin(db_session) -> None:
    external_url = "https://jobs.ashbyhq.com/acme/123"
    encoded = quote(external_url, safe="")
    linkedin_url = (
        "https://www.linkedin.com/jobs/view/externalApply/?"
        f"url={encoded}&tracking=foo"
    )
    html = (
        "<html><body>"
        '<code id="applyUrl" style="display:none">'
        f'<!--"{linkedin_url}"-->'
        "</code>"
        '<section class="core-section-container my-3 description">'
        "Role details"
        "</section>"
        "</body></html>"
    )

    job = Job(
        title="Data Engineer",
        company="Acme",
        source=Source.LINKEDIN,
        source_url="https://www.linkedin.com/jobs/view/123",
        listing_remote=RemoteStatus.UNKNOWN,
    )
    db_session.add(job)
    db_session.commit()

    handler = CareerPageHandler(db_session)
    session = _FakeSession(_FakeResponse(html))

    job_analyser._apply_description_analysis(job, session, handler)

    page = handler.get_by_url("https://jobs.ashbyhq.com/acme")
    assert page is not None
    assert page.company_name == "acme"
