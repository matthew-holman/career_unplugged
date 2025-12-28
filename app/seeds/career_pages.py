# app/seed/career_pages_seeder.py
from dataclasses import dataclass

from sqlmodel import Session, select

from app.models.career_page import CareerPage
from app.seeds.data.team_tailor_pages import TEAM_TAILOR_PAGE_SEEDS


@dataclass
class CareerPageSeeder:
    db_session: Session

    def run(self) -> None:
        for seed in TEAM_TAILOR_PAGE_SEEDS:
            url = seed["url"].rstrip("/")  # type: ignore[attr-defined]
            existing = self.db_session.exec(
                select(CareerPage).where(CareerPage.url == url)
            ).first()

            if existing is None:
                self.db_session.add(CareerPage(**{**seed, "url": url}))
                continue

            # Only backfill missing fields; do not overwrite user edits.
            if existing.company_name is None and seed.get("company_name"):
                existing.company_name = seed["company_name"]

            if existing.ats_provider is None and seed.get("ats_provider"):
                existing.ats_provider = seed["ats_provider"]

            if existing.active is None and seed.get("active") is not None:
                existing.active = seed["active"]

            self.db_session.add(existing)

        self.db_session.commit()
