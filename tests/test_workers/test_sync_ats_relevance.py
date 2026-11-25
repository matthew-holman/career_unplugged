from dataclasses import dataclass

import pytest

from sqlmodel import Session

from app.job_scrapers.scraper import JobPost, JobResponse, Location, RemoteStatus
from app.models.career_page import CareerPage, CareerPageRelevance
from app.workers import sync_ats


@dataclass
class _FakeScraper:
    response: JobResponse

    def scrape(self) -> JobResponse:
        return self.response


def _response(*countries: str) -> JobResponse:
    return JobResponse(
        jobs=[
            JobPost(
                title="Engineer",
                job_url=f"https://example.com/{country}",
                location=Location(country=country),
                remote_status=RemoteStatus.ONSITE,
            )
            for country in countries
        ]
    )


def test_sync_rates_page_and_then_holds_it_back(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = CareerPage(company_name="Acme", url="https://acme.example.com")
    db_session.add(page)
    db_session.commit()

    monkeypatch.setattr(
        sync_ats.AtsScraperFactory,
        "get_ats_scraper",
        lambda _page: _FakeScraper(_response("United States", "India")),
    )

    summary = sync_ats.run_sync_ats_with_session(db_session)
    db_session.refresh(page)
    assert summary["pages_reclassified"] == 1
    assert page.relevance == CareerPageRelevance.OUTSIDE_EUROPE

    # Freshly synced and outside Europe: skipped until it is due a re-check.
    summary = sync_ats.run_sync_ats_with_session(db_session)
    assert summary["pages_selected"] == 0

    summary = sync_ats.run_sync_ats_with_session(db_session, include_low_relevance=True)
    assert summary["pages_selected"] == 1
