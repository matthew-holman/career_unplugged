"""Tests for RemoteScorer — graduated remote eligibility scoring."""

import pytest

from app.job_scrapers.scraper import RemoteStatus, Source
from app.models.job import Job
from app.utils.locations.remote_scorer import RemoteScorer


def _job(
    title: str = "Engineering Manager",
    country: str | None = None,
    listing_remote: RemoteStatus | None = RemoteStatus.UNKNOWN,
) -> Job:
    return Job(
        title=title,
        company="Acme",
        source=Source.ASHBY,
        country=country,
        listing_remote=listing_remote,
    )


# ---------------------------------------------------------------------------
# Location-based scoring
# ---------------------------------------------------------------------------


def test_emea_location_scores_4() -> None:
    job = _job(country="EMEA")
    score, _ = RemoteScorer.score(job, None)
    assert score == 4


def test_europe_location_scores_4() -> None:
    job = _job(country="Europe")
    score, _ = RemoteScorer.score(job, None)
    assert score == 4


def test_european_union_location_scores_4() -> None:
    job = _job(country="European Union")
    score, _ = RemoteScorer.score(job, None)
    assert score == 4


def test_sweden_remote_listing_scores_3() -> None:
    job = _job(country="Sweden", listing_remote=RemoteStatus.REMOTE)
    score, _ = RemoteScorer.score(job, None)
    assert score == 3


def test_germany_remote_listing_scores_3() -> None:
    job = _job(country="Germany", listing_remote=RemoteStatus.REMOTE)
    score, _ = RemoteScorer.score(job, None)
    assert score == 3


def test_hybrid_listing_scores_2() -> None:
    job = _job(country="Sweden", listing_remote=RemoteStatus.HYBRID)
    score, _ = RemoteScorer.score(job, None)
    assert score == 2


def test_onsite_listing_scores_0() -> None:
    job = _job(country="Sweden", listing_remote=RemoteStatus.ONSITE)
    score, _ = RemoteScorer.score(job, None)
    assert score == 0


# ---------------------------------------------------------------------------
# Title-based scoring
# ---------------------------------------------------------------------------


def test_remote_in_title_scores_at_least_3() -> None:
    job = _job(title="Remote Engineering Manager")
    score, _ = RemoteScorer.score(job, None)
    assert score >= 3


def test_emea_in_title_scores_at_least_2() -> None:
    job = _job(title="Engineering Manager, EMEA")
    score, _ = RemoteScorer.score(job, None)
    assert score >= 2


# ---------------------------------------------------------------------------
# Description-based scoring — score 5
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "We are a remote-first company.",
        "Our team is remote first.",
        "100% remote role.",
        "Fully remote position available.",
        "We operate as a fully distributed team.",
        "async-first culture.",
    ],
)
def test_score_5_descriptions(text: str) -> None:
    job = _job()
    score, _ = RemoteScorer.score(job, text)
    assert score == 5


# ---------------------------------------------------------------------------
# Description-based scoring — score 4
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Work remotely within Europe.",
        "You can work from anywhere in Europe.",
        "We are location agnostic.",
        "This is a remote-friendly role.",
        "Remote in EU candidates welcome.",
        "Open to remote candidates.",
        "Work anywhere in EMEA.",
    ],
)
def test_score_4_descriptions(text: str) -> None:
    job = _job()
    score, _ = RemoteScorer.score(job, text)
    assert score >= 4


# ---------------------------------------------------------------------------
# Description-based scoring — score 3
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "You must be available in Western European timezones.",
        "Working hours align with European timezones.",
        "Flexible location policy.",
        "No relocation required.",
        "We are a distributed team.",
        "Candidates across EMEA are welcome.",
    ],
)
def test_score_3_descriptions(text: str) -> None:
    job = _job()
    score, _ = RemoteScorer.score(job, text)
    assert score >= 3


# ---------------------------------------------------------------------------
# Description-based scoring — score 2 (timezone-only signals)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Meetings are held in CET.",
        "Please be available UTC+1.",
        "We use Employer of Record for international hires.",
    ],
)
def test_score_2_descriptions(text: str) -> None:
    job = _job()
    score, _ = RemoteScorer.score(job, text)
    assert score == 2


# ---------------------------------------------------------------------------
# False positive suppression
# ---------------------------------------------------------------------------


def test_work_from_anywhere_up_to_weeks_does_not_score_high() -> None:
    """Workcation policy should not be treated as remote work."""
    job = _job()
    text = "You can work from anywhere up to 4 weeks a year."
    score, _ = RemoteScorer.score(job, text)
    assert score < 4


def test_work_from_anywhere_in_specific_country_does_not_score_high() -> None:
    """Country-restricted 'anywhere' is not EU-remote."""
    job = _job()
    text = "You can work from anywhere in Germany."
    score, _ = RemoteScorer.score(job, text)
    assert score < 4


def test_work_from_anywhere_in_europe_scores_high() -> None:
    """European-qualified 'anywhere' should still score high."""
    job = _job()
    text = "You can work from anywhere in Europe."
    score, _ = RemoteScorer.score(job, text)
    assert score >= 4


# ---------------------------------------------------------------------------
# ONSITE listing caps score
# ---------------------------------------------------------------------------


def test_onsite_listing_caps_score_even_with_strong_description() -> None:
    job = _job(listing_remote=RemoteStatus.ONSITE)
    text = "We are a remote-first async-first company."
    score, _ = RemoteScorer.score(job, text)
    assert score <= 2


# ---------------------------------------------------------------------------
# set_remote_score derives true_remote correctly
# ---------------------------------------------------------------------------


def test_set_remote_score_3_sets_true_remote_true() -> None:
    job = _job()
    job.set_remote_score(3, "Sweden Remote")
    assert job.true_remote is True
    assert job.remote_score == 3
    assert job.remote_flag_reason == "Sweden Remote"


def test_set_remote_score_2_sets_true_remote_false() -> None:
    job = _job()
    job.set_remote_score(2, "Hybrid listing")
    assert job.true_remote is False
    assert job.remote_score == 2


def test_set_remote_score_0_sets_true_remote_false() -> None:
    job = _job()
    job.set_remote_score(0, "Onsite listing")
    assert job.true_remote is False
    assert job.remote_score == 0
