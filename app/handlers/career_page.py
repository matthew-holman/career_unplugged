from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Sequence

from sqlalchemy import desc, func, nulls_last, or_
from sqlmodel import Session, col, select

from app.filters.career_page_filter import CareerPageFilter
from app.models.career_page import CareerPage, CareerPageCreate, CareerPageRead


@dataclass
class CareerPageHandler:
    db_session: Session

    def get_by_id(self, page_id: int) -> Optional[CareerPage]:
        statement = select(CareerPage).where(CareerPage.id == page_id)
        return self.db_session.exec(statement).first()

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
    ) -> List[CareerPage]:
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
        else:
            query = query.where(col(CareerPage.last_synced_at).is_(None))

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

    def deactivate(self, career_page: CareerPage, status_code: int) -> None:
        career_page.active = False
        career_page.deactivated_at = datetime.now(timezone.utc)
        career_page.last_status_code = status_code
        self.db_session.add(career_page)
