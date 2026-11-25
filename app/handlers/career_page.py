from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Mapping, Optional, Sequence

from sqlalchemy import and_, desc, func, nulls_last, or_
from sqlmodel import Session, col, select

from app.filters.career_page_filter import CareerPageFilter
from app.models.career_page import (
    CareerPage,
    CareerPageCreate,
    CareerPageRead,
    CareerPageRelevance,
)


@dataclass
class CareerPageHandler:
    db_session: Session

    def get_by_id(self, page_id: int) -> Optional[CareerPage]:
        statement = select(CareerPage).where(CareerPage.id == page_id)
        return self.db_session.exec(statement).first()

    def get_by_url(self, url: str) -> Optional[CareerPage]:
        statement = select(CareerPage).where(
            func.lower(col(CareerPage.url)) == url.lower()
        )
        return self.db_session.exec(statement).first()

    def upsert_discovered(
        self, page: CareerPageCreate
    ) -> tuple[CareerPage | None, bool]:
        existing = self.get_by_url(page.url)
        if existing:
            if not existing.active:
                return None, False
            if page.company_name and not existing.company_name:
                existing.company_name = page.company_name
                self.db_session.add(existing)
                self.db_session.flush()
            return existing, False

        validated_page = CareerPage.model_validate(page)
        self.db_session.add(validated_page)
        self.db_session.flush()
        return validated_page, True

    def list(self, filters: CareerPageFilter) -> list[CareerPage]:
        query = select(CareerPage)
        provided = filters.model_dump(exclude_none=True)

        filter_builders = {
            "company_name": lambda value: func.lower(
                col(CareerPage.company_name)
            ).contains(value.lower()),
            "url": lambda value: func.lower(col(CareerPage.url)).contains(
                value.lower()
            ),
            "active": lambda value: col(CareerPage.active) == value,
            "last_synced_at_gte": lambda value: (
                col(CareerPage.last_synced_at) >= value
            ),
            "last_synced_at_lte": lambda value: (
                col(CareerPage.last_synced_at) <= value
            ),
            "deactivated_at_gte": lambda value: (
                col(CareerPage.deactivated_at) >= value
            ),
            "deactivated_at_lte": lambda value: (
                col(CareerPage.deactivated_at) <= value
            ),
            "last_status_code": lambda value: (
                col(CareerPage.last_status_code) == value
            ),
            "relevance": lambda value: col(CareerPage.relevance) == value,
            "relevance_locked": lambda value: (
                col(CareerPage.relevance_locked) == value
            ),
        }

        for field_name, value in provided.items():
            builder = filter_builders.get(field_name)
            if builder is not None:
                query = query.where(builder(value))

        query = query.order_by(
            nulls_last(desc(CareerPage.last_synced_at)), desc(CareerPage.id)  # type: ignore[arg-type]
        )
        return self.db_session.exec(query).all()

    def select_for_sync(
        self,
        career_page_ids: List[int] | None,
        max_age_hours: int | None,
        include_inactive: bool,
        relevance_rescan_days: Mapping[CareerPageRelevance, int] | None = None,
    ) -> List[CareerPage]:
        """Select pages to scan.

        ``relevance_rescan_days`` holds back pages of the given relevance
        until that many days after their last sync. It does not apply when
        ``career_page_ids`` names the pages.
        """
        query = select(CareerPage)
        if not include_inactive:
            query = query.where(col(CareerPage.active).is_(True))

        if career_page_ids:
            query = query.where(CareerPage.id.in_(career_page_ids))  # type: ignore[attr-defined]
            return self.db_session.exec(query).all()

        if max_age_hours is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            query = query.where(
                or_(
                    col(CareerPage.last_synced_at).is_(None),
                    col(CareerPage.last_synced_at) < cutoff,
                )
            )

        if relevance_rescan_days:
            now = datetime.now(timezone.utc)
            query = query.where(
                or_(
                    col(CareerPage.relevance).not_in(list(relevance_rescan_days)),
                    col(CareerPage.last_synced_at).is_(None),
                    *(
                        and_(
                            col(CareerPage.relevance) == relevance,
                            col(CareerPage.last_synced_at) < now - timedelta(days=days),
                        )
                        for relevance, days in relevance_rescan_days.items()
                    ),
                )
            )

        return self.db_session.exec(query).all()

    def get_all_active(self) -> Sequence[CareerPage]:
        statement = select(CareerPage).where(col(CareerPage.active).is_(True))
        return self.db_session.exec(statement).all()

    def create(self, page: CareerPageCreate) -> CareerPageRead:
        validated_page = CareerPage.model_validate(page)
        self.db_session.add(validated_page)
        self.db_session.commit()
        self.db_session.refresh(validated_page)
        return CareerPageRead.model_validate(validated_page)

    def update(
        self, page_id: int, update: CareerPageCreate
    ) -> Optional[CareerPageRead]:
        page = self.get_by_id(page_id)
        if not page:
            return None
        for field, value in update.model_dump(exclude_unset=True).items():
            setattr(page, field, value)
        self.db_session.add(page)
        self.db_session.commit()
        self.db_session.refresh(page)
        return CareerPageRead.model_validate(page)

    def deactivate(
        self, career_page: CareerPage, status_code: int | None = None
    ) -> None:
        career_page.active = False
        career_page.deactivated_at = datetime.now(timezone.utc)
        if status_code is not None:
            career_page.last_status_code = status_code
        self.db_session.add(career_page)
