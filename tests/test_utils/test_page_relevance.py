import pytest

from app.job_scrapers.scraper import JobPost, Location, RemoteStatus
from app.models.career_page import CareerPage, CareerPageRelevance
from app.utils.locations.page_relevance import classify_career_page, classify_job_post


def _post(
    country: str | None = None,
    city: str | None = None,
    remote_status: RemoteStatus | None = RemoteStatus.ONSITE,
) -> JobPost:
    location = Location(country=country, city=city) if country or city else None
    return JobPost(
        title="Engineer",
        job_url="https://example.com/job",
        location=location,
        remote_status=remote_status,
    )


@pytest.mark.parametrize(
    ("post", "expected"),
    [
        (_post(country="Sweden"), CareerPageRelevance.TARGET),
        (_post(city="Gothenburg"), CareerPageRelevance.TARGET),
        (
            _post(country="Germany", remote_status=RemoteStatus.REMOTE),
            CareerPageRelevance.TARGET,
        ),
        (_post(country="Remote"), CareerPageRelevance.TARGET),
        (_post(remote_status=RemoteStatus.REMOTE), CareerPageRelevance.TARGET),
        (
            _post(country="United States", remote_status=RemoteStatus.REMOTE),
            CareerPageRelevance.REMOTE_OUTSIDE_EUROPE,
        ),
        (
            _post(country="Germany", remote_status=RemoteStatus.HYBRID),
            CareerPageRelevance.EUROPE_ONSITE,
        ),
        (_post(country="United States"), CareerPageRelevance.OUTSIDE_EUROPE),
        (_post(), CareerPageRelevance.UNKNOWN),
    ],
)
def test_classify_job_post(post: JobPost, expected: CareerPageRelevance) -> None:
    assert classify_job_post(post) == expected


def test_page_takes_its_most_relevant_job() -> None:
    posts = [
        _post(country="United States"),
        _post(country="France"),
        _post(),
    ]
    assert classify_career_page(posts) == CareerPageRelevance.EUROPE_ONSITE

    posts.append(_post(country="Sweden"))
    assert classify_career_page(posts) == CareerPageRelevance.TARGET


def test_page_with_only_outside_europe_onsite_jobs() -> None:
    posts = [_post(country="United States"), _post(country="India")]
    assert classify_career_page(posts) == CareerPageRelevance.OUTSIDE_EUROPE


def test_empty_page_is_unknown() -> None:
    assert classify_career_page([]) == CareerPageRelevance.UNKNOWN


def test_apply_scanned_relevance() -> None:
    page = CareerPage(url="https://example.com")
    assert page.apply_scanned_relevance(CareerPageRelevance.OUTSIDE_EUROPE)
    assert page.relevance == CareerPageRelevance.OUTSIDE_EUROPE

    # Same value, or an empty scan, changes nothing.
    assert not page.apply_scanned_relevance(CareerPageRelevance.OUTSIDE_EUROPE)
    assert not page.apply_scanned_relevance(CareerPageRelevance.UNKNOWN)
    assert page.relevance == CareerPageRelevance.OUTSIDE_EUROPE


def test_locked_relevance_is_kept() -> None:
    page = CareerPage(
        url="https://example.com",
        relevance=CareerPageRelevance.TARGET,
        relevance_locked=True,
    )
    assert not page.apply_scanned_relevance(CareerPageRelevance.OUTSIDE_EUROPE)
    assert page.relevance == CareerPageRelevance.TARGET
