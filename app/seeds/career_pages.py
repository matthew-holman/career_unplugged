# app/seed/career_pages_seeder.py
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from sqlmodel import Session, select

from app.models.career_page import CareerPage
from app.seeds.data.ashby_pages import ASHBY_PAGE_SEEDS
from app.seeds.data.bamboo_pages import BAMBOO_PAGE_SEEDS
from app.seeds.data.career_pages import CAREER_PAGE_SEEDS
from app.seeds.data.dover_pages import DOVER_PAGE_SEEDS
from app.seeds.data.greenhouse_pages import GREENHOUSE_PAGE_SEEDS
from app.seeds.data.hibob_pages import HIBOB_PAGE_SEEDS
from app.seeds.data.jobylon_pages import JOBYLON_PAGE_SEEDS
from app.seeds.data.lever_pages import LEVER_PAGE_SEEDS
from app.seeds.data.people_force_pages import PEOPLE_FORCE_PAGE_SEEDS
from app.seeds.data.personio_pages import PERSONIO_PAGE_SEEDS
from app.seeds.data.recruitee_pages import RECRUITEE_PAGE_SEEDS
from app.seeds.data.rippling_pages import RIPPLING_PAGE_SEEDS
from app.seeds.data.sloneek_pages import SLONEEK_PAGE_SEEDS
from app.seeds.data.team_tailor_pages import TEAM_TAILOR_PAGE_SEEDS
from app.seeds.data.workable_pages import WORKABLE_PAGE_SEEDS

SEED_LISTS = [
    ASHBY_PAGE_SEEDS,
    BAMBOO_PAGE_SEEDS,
    CAREER_PAGE_SEEDS,
    DOVER_PAGE_SEEDS,
    GREENHOUSE_PAGE_SEEDS,
    HIBOB_PAGE_SEEDS,
    JOBYLON_PAGE_SEEDS,
    LEVER_PAGE_SEEDS,
    PEOPLE_FORCE_PAGE_SEEDS,
    PERSONIO_PAGE_SEEDS,
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
            self.seed(seed_page_list)
        self.db_session.commit()

    def seed(self, seeds: Iterable[Mapping[str, object]]) -> int:
        """
        Insert seeds whose URL is not in the database yet; backfill a missing
        company name on existing pages. Does not commit. Returns the number of
        pages inserted.
        """
        created = 0
        for seed in seeds:
            raw_url = seed.get("url")
            if not isinstance(raw_url, str):
                continue
            url = raw_url.rstrip("/")
            existing = self.db_session.exec(
                select(CareerPage).where(CareerPage.url == url)
            ).first()

            if existing is None:
                self.db_session.add(CareerPage(**{**seed, "url": url}))
                created += 1
                continue

            # Only backfill missing fields; do not overwrite user edits.
            company_name = seed.get("company_name")
            if existing.company_name is None and isinstance(company_name, str):
                existing.company_name = company_name

            self.db_session.add(existing)
        return created
