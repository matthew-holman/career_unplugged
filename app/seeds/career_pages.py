# app/seed/career_pages_seeder.py
from dataclasses import dataclass

from sqlmodel import Session, select

from app.models.career_page import CareerPage
from app.seeds.data.ashby_pages import ASHBY_PAGE_SEEDS
from app.seeds.data.career_pages import CAREER_PAGE_SEEDS
from app.seeds.data.greenhouse_pages import GREENHOUSE_PAGE_SEEDS
from app.seeds.data.hibob_pages import HIBOB_PAGE_SEEDS
from app.seeds.data.lever_pages import LEVER_PAGE_SEEDS
from app.seeds.data.people_force_pages import PEOPLE_FORCE_PAGE_SEEDS
from app.seeds.data.recruitee_pages import RECRUITEE_PAGE_SEEDS
from app.seeds.data.rippling_pages import RIPPLING_PAGE_SEEDS
from app.seeds.data.sloneek_pages import SLONEEK_PAGE_SEEDS
from app.seeds.data.team_tailor_pages import TEAM_TAILOR_PAGE_SEEDS
from app.seeds.data.workable_pages import WORKABLE_PAGE_SEEDS

SEED_LISTS = [
    ASHBY_PAGE_SEEDS,
    CAREER_PAGE_SEEDS,
    GREENHOUSE_PAGE_SEEDS,
    HIBOB_PAGE_SEEDS,
    LEVER_PAGE_SEEDS,
    PEOPLE_FORCE_PAGE_SEEDS,
    RECRUITEE_PAGE_SEEDS,
    RIPPLING_PAGE_SEEDS,
    SLONEEK_PAGE_SEEDS,
    TEAM_TAILOR_PAGE_SEEDS,
    WORKABLE_PAGE_SEEDS,
]


@dataclass
class CareerPageSeeder:
    db_session: Session

    def run(self) -> None:
        for seed_page_list in SEED_LISTS:
            for seed in seed_page_list:
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

                if existing.active is None and seed.get("active") is not None:
                    existing.active = seed["active"]

                self.db_session.add(existing)

        self.db_session.commit()
