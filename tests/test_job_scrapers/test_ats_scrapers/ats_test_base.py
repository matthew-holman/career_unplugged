from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar

from bs4 import BeautifulSoup

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.models import CareerPage


@dataclass(frozen=True)
class AtsScraperTestResult:
    jobs_count: int
    parse_failures: int
    cards_count: int


ScraperType = TypeVar("ScraperType", bound=AtsScraper)


def run_ats_scraper_test(
    *,
    scraper_cls: type[ScraperType],
    career_page: CareerPage,
    # optional extra assertions/hooks per ATS
    assert_job_post: Callable[[object, CareerPage, AtsScraper], None] | None = None,
) -> AtsScraperTestResult:
    """
    Networked smoke/integration test harness for ATS scrapers.

    It exercises the same high-level steps as AtsScraper.scrape(), but keeps
    intermediate objects (soup/cards) available for debugging.

    Usage:
      run_ats_scraper_smoke_test(scraper_cls=GreenHouseBoardScraper, career_page=...)
    """
    supports = scraper_cls.supports(career_page.url)
    assert supports is True, f"{scraper_cls.__name__}.supports() returned False"

    scraper = scraper_cls(career_page)

    response = scraper._fetch_jobs_page(career_page.url)
    assert response is not None, "fetch returned None"

    soup = BeautifulSoup(response.text, "html.parser")

    job_cards = list(scraper.find_job_cards(soup))
    assert job_cards, "no job cards found"

    jobs = []
    parse_failures = 0

    for card in job_cards:
        job_post = scraper.parse_job_card(card)
        if not job_post:
            parse_failures += 1
            continue

        # Base assertions (common to all ATS scrapers)
        assert getattr(job_post, "title", None)
        assert getattr(job_post, "job_url", None)
        assert job_post.company_name == career_page.company_name
        assert job_post.source == scraper.source_name

        if assert_job_post:
            assert_job_post(job_post, career_page, scraper)

        jobs.append(job_post)

    assert parse_failures == 0, f"{parse_failures} job cards failed to parse"
    assert jobs, "no parsed jobs produced"

    return AtsScraperTestResult(
        jobs_count=len(jobs),
        parse_failures=parse_failures,
        cards_count=len(job_cards),
    )
