"""Analyser fetch behaviour: LinkedIn pacing and stopping cleanly when rate-limited."""

import pytest
import requests

from sqlmodel import Session, select

from app.job_scrapers.scraper import Source
from app.models.job import Job
from app.workers import job_analyser

LINKEDIN_PAGE = (
    "<html><body>"
    '<section class="core-section-container my-3 description">Role details</section>'
    "</body></html>"
)


class _FakeResponse:
    __slots__ = ("status_code", "text")

    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


class _FakeSession:
    """Returns the queued responses in order, or raises queued exceptions."""

    def __init__(self, *outcomes: object) -> None:
        self._outcomes = list(outcomes)
        self.urls: list[str] = []

    def get(self, url: str, **kwargs: object) -> _FakeResponse:
        self.urls.append(url)
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        assert isinstance(outcome, _FakeResponse)
        return outcome


class _SessionContext:
    """Stands in for `next(get_db())` without closing the test session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def __enter__(self) -> Session:
        return self._session

    def __exit__(self, *exc: object) -> None:
        return None


def _linkedin_job(n: int) -> Job:
    return Job(
        title=f"Engineering Manager {n}",
        company="acme",
        country="Sweden",
        source=Source.LINKEDIN,
        linkedin_source_url=f"https://www.linkedin.com/jobs/view/{n}",
    )


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    sleeps: list[float] = []
    monkeypatch.setattr(job_analyser.time, "sleep", sleeps.append)
    return sleeps


# ---------------------------------------------------------------------------
# Throttle
# ---------------------------------------------------------------------------


def test_throttle_waits_between_linkedin_fetches_only(no_sleep: list[float]) -> None:
    throttle = job_analyser._LinkedInThrottle()

    throttle.wait("https://www.linkedin.com/jobs/view/1")
    throttle.wait("https://jobs.ashbyhq.com/acme/1")
    throttle.wait("https://www.linkedin.com/jobs/view/2")
    throttle.wait("https://www.linkedin.com/jobs/view/3")

    low, high = job_analyser.LINKEDIN_FETCH_DELAY_SECONDS
    assert len(no_sleep) == 2
    assert all(low <= delay <= high for delay in no_sleep)


# ---------------------------------------------------------------------------
# _fetch_job_page error mapping
# ---------------------------------------------------------------------------


def test_fetch_raises_rate_limited_on_429_response() -> None:
    session = _FakeSession(_FakeResponse(429))
    with pytest.raises(job_analyser.RateLimitedError):
        job_analyser._fetch_job_page(session, _linkedin_job(1))


def test_fetch_raises_rate_limited_when_429_retries_exhausted() -> None:
    error = requests.exceptions.RetryError("too many 429 error responses")
    with pytest.raises(job_analyser.RateLimitedError):
        job_analyser._fetch_job_page(_FakeSession(error), _linkedin_job(1))


def test_fetch_raises_fetch_failed_on_network_error() -> None:
    error = requests.exceptions.ConnectionError("connection reset")
    with pytest.raises(job_analyser.FetchFailedError):
        job_analyser._fetch_job_page(_FakeSession(error), _linkedin_job(1))


def test_fetch_returns_none_for_removed_page() -> None:
    session = _FakeSession(_FakeResponse(404))
    assert job_analyser._fetch_job_page(session, _linkedin_job(1)) is None


# ---------------------------------------------------------------------------
# run_analyser
# ---------------------------------------------------------------------------


def _run(
    monkeypatch: pytest.MonkeyPatch, db_session: Session, session: _FakeSession
) -> None:
    monkeypatch.setattr(
        job_analyser, "get_db", lambda: iter([_SessionContext(db_session)])
    )
    monkeypatch.setattr(job_analyser, "create_session", lambda **kwargs: session)
    job_analyser.run_analyser()


def test_run_stops_on_rate_limit_and_keeps_earlier_results(
    monkeypatch: pytest.MonkeyPatch, db_session: Session, no_sleep: list[float]
) -> None:
    db_session.add_all([_linkedin_job(n) for n in range(1, 4)])
    db_session.commit()
    session = _FakeSession(
        _FakeResponse(200, LINKEDIN_PAGE),
        _FakeResponse(429),
    )

    _run(monkeypatch, db_session, session)

    jobs = db_session.exec(select(Job)).all()
    assert len(session.urls) == 2, "should stop after the first 429"
    assert sum(job.analysed for job in jobs) == 1
    assert sum(not job.analysed for job in jobs) == 2


def test_run_skips_unfetchable_job_and_continues(
    monkeypatch: pytest.MonkeyPatch, db_session: Session, no_sleep: list[float]
) -> None:
    db_session.add_all([_linkedin_job(n) for n in range(1, 3)])
    db_session.commit()
    session = _FakeSession(
        requests.exceptions.ConnectionError("connection reset"),
        _FakeResponse(200, LINKEDIN_PAGE),
    )

    _run(monkeypatch, db_session, session)

    jobs = db_session.exec(select(Job)).all()
    assert len(session.urls) == 2
    assert sum(job.analysed for job in jobs) == 1
    assert len(no_sleep) == 1
