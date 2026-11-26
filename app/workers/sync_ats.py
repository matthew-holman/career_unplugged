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
    NoScraperMatchedError,
)
from app.log import Log
from app.models.career_page import CareerPage
from app.models.job import Job
from app.search_profile import RELEVANCE_RESCAN_DAYS, UNSUPPORTED_RECHECK_DAYS
from app.settings import settings
from app.utils.locations.page_relevance import classify_career_page
from app.workers.job_analyser import run_analyser
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
    include_low_relevance: bool = False,
    include_unsupported: bool = False,
) -> dict[str, Any]:
    load_dotenv()
    Log.setup(application_name="sync_ats")

    with next(get_db()) as db_session:
        return run_sync_ats_with_session(
            db_session,
            career_page_ids=career_page_ids,
            max_age_hours=max_age_hours,
            include_inactive=include_inactive,
            include_low_relevance=include_low_relevance,
            include_unsupported=include_unsupported,
        )


def run_sync_ats_with_session(
    db_session: Session,
    *,
    career_page_ids: list[int] | None = None,
    max_age_hours: int | None = None,
    include_inactive: bool = False,
    include_low_relevance: bool = False,
    include_unsupported: bool = False,
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
    pages_reclassified = 0
    pages_unsupported = 0

    career_pages = page_handler.select_for_sync(
        career_page_ids=career_page_ids,
        max_age_hours=max_age_hours,
        include_inactive=include_inactive,
        relevance_rescan_days=None if include_low_relevance else RELEVANCE_RESCAN_DAYS,
        unsupported_recheck_days=(
            None if include_unsupported else UNSUPPORTED_RECHECK_DAYS
        ),
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
        except NoScraperMatchedError:
            page.record_scraper_check(
                supported=False, checked_at=datetime.now(timezone.utc)
            )
            pending_pages.append(page)
            pending_pages = flush_pending_pages(
                db_session,
                pending_pages,
                batch_size=batch_size,
            )
            pages_unsupported += 1
            continue
        if not ats_scraper:
            Log.warning(f"Could not fetch career page {page.url}")
            continue
        page.record_scraper_check(supported=True, checked_at=datetime.now(timezone.utc))

        try:
            response = ats_scraper.scrape()
        except Exception as exc:
            Log.error(
                f"Unexpected error scraping {page.url} — skipping. {exc.__class__.__name__}: {exc}"
            )
            continue
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

        previous_relevance = page.relevance
        if page.apply_scanned_relevance(classify_career_page(response.jobs)):
            pages_reclassified += 1
            Log.info(
                f"Career page {page.url} relevance "
                f"{previous_relevance.value} -> {page.relevance.value}"
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
        "pages_reclassified": pages_reclassified,
        "pages_unsupported": pages_unsupported,
        "jobs_processed": jobs_processed,
        "jobs_saved": jobs_saved,
    }


def main() -> int:
    run_sync_ats()
    run_analyser()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
