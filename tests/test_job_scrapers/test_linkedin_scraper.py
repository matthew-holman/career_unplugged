import re

import pytest

from app.job_scrapers.linkedin import LinkedInScraper
from app.job_scrapers.scraper import JobType, RemoteStatus, ScraperInput

SEARCH_URL = re.compile(
    r"https://www\.linkedin\.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
)

SEARCH_CARD_HTML = """
<div class="base-search-card">
  <a class="base-card__full-link"
     href="https://se.linkedin.com/jobs/view/senior-engineering-manager-at-tibber-4491943234?trk=x">
  </a>
  <span class="sr-only">Senior Engineering Manager</span>
  <h4 class="base-search-card__subtitle"><a href="https://se.linkedin.com/company/tibber">Tibber</a></h4>
  <div class="base-search-card__metadata">
    <span class="job-search-card__location">Stockholm, Stockholm County, Sweden</span>
    <time class="job-search-card__listdate" datetime="2026-11-20">1 day ago</time>
  </div>
</div>
"""


@pytest.mark.parametrize(
    "search_filter",
    [RemoteStatus.REMOTE, RemoteStatus.HYBRID, RemoteStatus.ONSITE, None],
)
def test_linkedin_jobs_are_unknown_regardless_of_search_filter(
    requests_mock, search_filter: RemoteStatus | None
) -> None:
    """LinkedIn's guest search ignores f_WT, so the filter must not set the status."""
    requests_mock.get(SEARCH_URL, text=SEARCH_CARD_HTML)

    response = LinkedInScraper().scrape(
        ScraperInput(
            search_term="engineering manager",
            location="Stockholm, Stockholm County, Sweden",
            job_type=JobType.FULL_TIME,
            results_wanted=1,
            remote_status=search_filter,
        )
    )

    assert len(response.jobs) == 1
    job = response.jobs[0]
    assert job.job_url == "https://www.linkedin.com/jobs/view/4491943234"
    assert job.remote_status == RemoteStatus.UNKNOWN
