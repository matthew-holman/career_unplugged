from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from sqlmodel import Session

from app.db.db import get_db
from app.handlers.career_page import CareerPageHandler
from app.handlers.job import JobHandler
from app.job_scrapers.ats_scraper_factory import (
    AtsScraperFactory,
    CareerPageDeactivatedError,
)
from app.log import Log
from app.models.career_page import CareerPage
from app.models.job import Job
from app.settings import settings
from app.workers.sync_common import (
    build_jobs_to_save,
    flush_pending_jobs,
    flush_pending_pages,
)


def run_sync_ats(
    *,
    career_page_ids: list[int] | None = None,
    max_age_hours: int | None = None,
    include_inactive: bool = False,
) -> dict[str, Any]:
    load_dotenv()
    Log.setup(application_name="sync_ats")

    with next(get_db()) as db_session:
        return run_sync_ats_with_session(
            db_session,
            career_page_ids=career_page_ids,
            max_age_hours=max_age_hours,
            include_inactive=include_inactive,
        )


def run_sync_ats_with_session(
    db_session: Session,
    *,
    career_page_ids: list[int] | None = None,
    max_age_hours: int | None = None,
    include_inactive: bool = False,
) -> dict[str, Any]:
    job_handler = JobHandler(db_session)
    page_handler = CareerPageHandler(db_session)
    batch_size = settings.DB_BATCH_SIZE

    pending_jobs: list[Job] = []
    pending_pages: list[CareerPage] = []

    jobs_processed = 0
    jobs_saved = 0
    pages_synced = 0
    pages_deactivated = 0

    career_pages = page_handler.select_for_sync(
        career_page_ids=career_page_ids,
        max_age_hours=max_age_hours,
        include_inactive=include_inactive,
    )
    pages_selected = len(career_pages)

    for page in career_pages:
        Log.info(f"Processing {page.company_name or page.url}")
        try:
            ats_scraper = AtsScraperFactory.get_ats_scraper(page)
        except CareerPageDeactivatedError as exc:
            page_handler.deactivate(page, exc.status_code)
            pending_pages.append(page)
            pending_pages = flush_pending_pages(
                db_session,
                pending_pages,
                batch_size=batch_size,
            )
            pages_deactivated += 1
            Log.warning(
                f"{AtsScraperFactory.__name__}: deactivated career page {page.url} "
                f"with status {exc.status_code}"
            )
            continue
        if not ats_scraper:
            Log.warning(f"No supported ATS parser for {page.url}")
            continue

        response = ats_scraper.scrape()
        pages_synced += 1
        jobs_processed += len(response.jobs)
        jobs_to_save = build_jobs_to_save(response, career_page_id=page.id)
        if jobs_to_save:
            jobs_saved += len(jobs_to_save)
            pending_jobs.extend(jobs_to_save)
            pending_jobs = flush_pending_jobs(
                db_session,
                job_handler,
                pending_jobs,
                batch_size=batch_size,
            )

        page.last_synced_at = datetime.now(timezone.utc)
        pending_pages.append(page)
        pending_pages = flush_pending_pages(
            db_session,
            pending_pages,
            batch_size=batch_size,
        )

    flush_pending_jobs(
        db_session,
        job_handler,
        pending_jobs,
        batch_size=batch_size,
        force=True,
    )
    flush_pending_pages(
        db_session,
        pending_pages,
        batch_size=batch_size,
        force=True,
    )

    return {
        "pages_selected": pages_selected,
        "pages_synced": pages_synced,
        "pages_deactivated": pages_deactivated,
        "jobs_processed": jobs_processed,
        "jobs_saved": jobs_saved,
    }


def main() -> int:
    run_sync_ats()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
