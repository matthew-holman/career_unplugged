from dataclasses import dataclass
from typing import List, Optional, Sequence

from sqlmodel import Session, select
from app.models.career_page import CareerPage, CareerPageCreate, CareerPageRead


@dataclass
class CareerPageHandler:
    db_session: Session

    def get(self, page_id: int) -> Optional[CareerPage]:
        statement = select(CareerPage).where(CareerPage.id == page_id)
        return self.db_session.exec(statement).first()

    def list_all(self) -> Sequence[CareerPage]:
        statement = select(CareerPage)
        return self.db_session.exec(statement).all()

    def create(self, page: CareerPageCreate) -> CareerPageRead:
        validated_page = CareerPage.model_validate(page)
        self.db_session.add(validated_page)
        self.db_session.commit()
        self.db_session.refresh(validated_page)
        return CareerPageRead.model_validate(validated_page)

    def update(self, page_id: int, update: CareerPageCreate) -> Optional[CareerPageRead]:
        page = self.get(page_id)
        if not page:
            return None
        for field, value in update.model_dump(exclude_unset=True).items():
            setattr(page, field, value)
        self.db_session.add(page)
        self.db_session.commit()
        self.db_session.refresh(page)
        return CareerPageRead.model_validate(page)