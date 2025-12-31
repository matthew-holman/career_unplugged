import pytest

from bs4 import BeautifulSoup

from app.job_scrapers.ats_scrapers.greenhouse_board_scraper import (
    GreenHouseBoardScraper,
)
from app.models import CareerPage


@pytest.mark.integration
@pytest.mark.network
def test_greenhouse_board_scraper() -> None:
    career_page = CareerPage(
        company_name="gitlab",
        url="https://job-boards.greenhouse.io/gitlab",
    )

    supports: bool = GreenHouseBoardScraper.supports(career_page.url)
    assert supports is True

    scraper = GreenHouseBoardScraper(career_page)

    response = scraper._fetch_jobs_page(career_page.url)
    assert response is not None

    soup = BeautifulSoup(response.text, "html.parser")

    job_cards = list(scraper.find_job_cards(soup))
    assert job_cards

    jobs = []
    parse_failures = 0

    for card in job_cards:
        job_post = scraper.parse_job_card(card)
        if not job_post:
            parse_failures += 1
            continue

        assert job_post.title
        assert job_post.job_url
        assert job_post.company_name == career_page.company_name
        assert job_post.source == scraper.source_name

        jobs.append(job_post)

    assert not parse_failures
    assert jobs
