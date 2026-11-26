from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from sqlmodel import Session

from app.job_scrapers.ats_scraper_factory import NoScraperMatchedError
from app.job_scrapers.scraper import JobResponse
from app.models.career_page import CareerPage, CareerPageScraperStatus
from app.search_profile import UNSUPPORTED_RECHECK_DAYS
from app.workers import sync_ats


@dataclass
class _FakeScraper:
    def scrape(self) -> JobResponse:
        return JobResponse(jobs=[])


def _no_scraper(page: CareerPage) -> _FakeScraper:
    raise NoScraperMatchedError(page.url)


def _add_page(db_session: Session) -> CareerPage:
    page = CareerPage(company_name="Acme", url="https://careers.acme.com")
    db_session.add(page)
    db_session.commit()
    return page


def test_sync_marks_unmatched_page_unsupported_and_holds_it_back(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = _add_page(db_session)
    monkeypatch.setattr(sync_ats.AtsScraperFactory, "get_ats_scraper", _no_scraper)

    summary = sync_ats.run_sync_ats_with_session(db_session)
    db_session.refresh(page)
    assert summary["pages_unsupported"] == 1
    assert page.scraper_status == CareerPageScraperStatus.UNSUPPORTED
    assert page.scraper_checked_at is not None
    assert page.active is True

    # Checked and unsupported: not fetched again until the re-check is due.
    summary = sync_ats.run_sync_ats_with_session(db_session)
    assert summary["pages_selected"] == 0

    summary = sync_ats.run_sync_ats_with_session(db_session, include_unsupported=True)
    assert summary["pages_selected"] == 1


def test_sync_rechecks_unsupported_page_once_due(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = _add_page(db_session)
    page.scraper_status = CareerPageScraperStatus.UNSUPPORTED
    page.scraper_checked_at = datetime.now(timezone.utc) - timedelta(
        days=UNSUPPORTED_RECHECK_DAYS + 1
    )
    db_session.add(page)
    db_session.commit()
    monkeypatch.setattr(
        sync_ats.AtsScraperFactory, "get_ats_scraper", lambda _page: _FakeScraper()
    )

    summary = sync_ats.run_sync_ats_with_session(db_session)
    db_session.refresh(page)
    assert summary["pages_selected"] == 1
    assert summary["pages_synced"] == 1
    assert page.scraper_status == CareerPageScraperStatus.SUPPORTED


def test_sync_leaves_status_alone_when_page_cannot_be_fetched(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = _add_page(db_session)
    monkeypatch.setattr(
        sync_ats.AtsScraperFactory, "get_ats_scraper", lambda _page: None
    )

    sync_ats.run_sync_ats_with_session(db_session)
    db_session.refresh(page)
    assert page.scraper_status == CareerPageScraperStatus.UNCHECKED
    assert page.scraper_checked_at is None
