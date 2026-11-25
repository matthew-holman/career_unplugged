import pytest

from sqlmodel import Session, select

from app.models.career_page import CareerPage
from app.workers import deactivate_vendor_career_pages


class _SessionContext:
    """Stands in for `next(get_db())` without closing the test session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def __enter__(self) -> Session:
        return self._session

    def __exit__(self, *exc: object) -> None:
        return None


@pytest.fixture()
def pages(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    monkeypatch.setattr(
        deactivate_vendor_career_pages,
        "get_db",
        lambda: iter([_SessionContext(db_session)]),
    )
    db_session.add_all(
        [
            CareerPage(company_name="acme", url="https://acme.teamtailor.com"),
            CareerPage(company_name="na", url="https://spokeo.na.teamtailor.com"),
            CareerPage(company_name="www", url="https://www.teamtailor.com"),
            CareerPage(company_name="status", url="https://status.recruitee.com"),
        ]
    )
    db_session.commit()


def _active_urls(db_session: Session) -> list[str]:
    pages = db_session.exec(select(CareerPage).where(CareerPage.active)).all()
    return sorted(page.url for page in pages)


@pytest.mark.usefixtures("pages")
def test_deactivates_vendor_hosts_only(db_session: Session) -> None:
    assert deactivate_vendor_career_pages.main([]) == 0

    assert _active_urls(db_session) == [
        "https://acme.teamtailor.com",
        "https://spokeo.na.teamtailor.com",
    ]
    vendor = db_session.exec(
        select(CareerPage).where(CareerPage.url == "https://www.teamtailor.com")
    ).one()
    assert vendor.deactivated_at is not None
    assert vendor.last_status_code is None


@pytest.mark.usefixtures("pages")
def test_dry_run_changes_nothing(db_session: Session) -> None:
    assert deactivate_vendor_career_pages.main(["--dry-run"]) == 0
    assert len(_active_urls(db_session)) == 4
