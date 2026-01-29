from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from app.handlers.career_page import CareerPageHandler
from app.models.career_page import CareerPage


def test_select_for_sync_max_age_hours(db_session: Session) -> None:
    now = datetime.now(timezone.utc)
    older = now - timedelta(hours=5)

    pages = [
        CareerPage(
            company_name="Old",
            url="https://old.example.com",
            active=True,
            last_synced_at=older,
        ),
        CareerPage(
            company_name="Recent",
            url="https://recent.example.com",
            active=True,
            last_synced_at=now,
        ),
        CareerPage(
            company_name="Never",
            url="https://never.example.com",
            active=True,
            last_synced_at=None,
        ),
    ]
    for page in pages:
        db_session.add(page)
    db_session.commit()

    handler = CareerPageHandler(db_session)
    results = handler.select_for_sync(
        career_page_ids=None,
        max_age_hours=2,
        include_inactive=False,
    )
    urls = {page.url for page in results}
    assert "https://old.example.com" in urls
    assert "https://never.example.com" in urls
    assert "https://recent.example.com" not in urls


def test_select_for_sync_ids_respects_active(db_session: Session) -> None:
    active_page = CareerPage(
        company_name="Active",
        url="https://active.example.com",
        active=True,
    )
    inactive_page = CareerPage(
        company_name="Inactive",
        url="https://inactive.example.com",
        active=False,
    )
    db_session.add(active_page)
    db_session.add(inactive_page)
    db_session.commit()

    handler = CareerPageHandler(db_session)
    results = handler.select_for_sync(
        career_page_ids=[active_page.id, inactive_page.id],
        max_age_hours=None,
        include_inactive=False,
    )
    ids = {page.id for page in results}
    assert active_page.id in ids
    assert inactive_page.id not in ids

    results = handler.select_for_sync(
        career_page_ids=[inactive_page.id],
        max_age_hours=None,
        include_inactive=True,
    )
    assert len(results) == 1
    assert results[0].id == inactive_page.id
