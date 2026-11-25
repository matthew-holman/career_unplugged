from __future__ import annotations

from collections.abc import Iterable

from app.job_scrapers.scraper import JobPost, RemoteStatus
from app.models.career_page import CareerPageRelevance
from app.search_profile import PREFERRED_LOCATIONS, TARGET_COUNTRIES
from app.utils.locations.europe_filter import EuropeFilter
from app.utils.locations.remote_filter import RemoteFilter

# Most relevant first: a page takes the rank of its most relevant job.
_RANK: tuple[CareerPageRelevance, ...] = (
    CareerPageRelevance.TARGET,
    CareerPageRelevance.REMOTE_OUTSIDE_EUROPE,
    CareerPageRelevance.EUROPE_ONSITE,
    CareerPageRelevance.OUTSIDE_EUROPE,
    CareerPageRelevance.UNKNOWN,
)

_TARGET_COUNTRIES = {country.lower() for country in TARGET_COUNTRIES}
_PREFERRED_LOCATIONS = {location.lower() for location in PREFERRED_LOCATIONS}


def classify_job_post(job_post: JobPost) -> CareerPageRelevance:
    """Rate one job by its location alone."""
    location = job_post.location
    country = (location.country or "").strip() if location else ""
    city = (location.city or "").strip() if location else ""

    if country.lower() in _TARGET_COUNTRIES or city.lower() in _PREFERRED_LOCATIONS:
        return CareerPageRelevance.TARGET

    remote = (
        job_post.remote_status == RemoteStatus.REMOTE
        or RemoteFilter.is_remote(country)
        or RemoteFilter.is_remote(city)
    )
    european = EuropeFilter.is_european(country)

    if remote:
        # Remote with no country, or a placeholder like "Remote"/"Worldwide",
        # can be done from Europe.
        if european or not country or RemoteFilter.is_remote(country):
            return CareerPageRelevance.TARGET
        return CareerPageRelevance.REMOTE_OUTSIDE_EUROPE

    if european:
        return CareerPageRelevance.EUROPE_ONSITE
    if country:
        return CareerPageRelevance.OUTSIDE_EUROPE
    return CareerPageRelevance.UNKNOWN


def classify_career_page(job_posts: Iterable[JobPost]) -> CareerPageRelevance:
    """Rate a career page by its most relevant job.

    UNKNOWN means the scan said nothing about where the company hires (no
    jobs, or no job with a usable location).
    """
    ranks = {classify_job_post(job_post) for job_post in job_posts}
    for relevance in _RANK:
        if relevance in ranks:
            return relevance
    return CareerPageRelevance.UNKNOWN
