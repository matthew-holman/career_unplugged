from __future__ import annotations

from typing import Any

from dotenv import load_dotenv
from sqlmodel import Session

from app.db.db import get_db
from app.handlers.job import JobHandler
from app.job_scrapers.linkedin import LinkedInScraper
from app.job_scrapers.scraper import JobType, RemoteStatus, ScraperInput
from app.log import Log
from app.models.job import Job
from app.search_profile import JOB_LOCATIONS, linkedin_search_string
from app.settings import settings
from app.workers.sync_common import build_jobs_to_save, flush_pending_jobs


def run_sync_linkedin() -> dict[str, Any]:
    load_dotenv()
    Log.setup(application_name="sync_linkedin")

    with next(get_db()) as db_session:
        return run_sync_linkedin_with_session(db_session)


def run_sync_linkedin_with_session(db_session: Session) -> dict[str, Any]:
    job_handler = JobHandler(db_session)
    batch_size = settings.DB_BATCH_SIZE
    pending_jobs: list[Job] = []
    jobs_processed = 0
    jobs_saved = 0

    scraper = LinkedInScraper()

    for job_location in JOB_LOCATIONS:
        Log.info(f"Scraping jobs for {job_location.location}")

        remote_statuses = [RemoteStatus.ONSITE, RemoteStatus.HYBRID]
        if job_location.remote:
            remote_statuses = [RemoteStatus.REMOTE]

        for remote_status in remote_statuses:
            Log.info(f"Scraping with remote status {remote_status.name}")

            scraper_input = ScraperInput(
                search_term=linkedin_search_string(),
                location=job_location.location,
                job_type=JobType.FULL_TIME,
                results_wanted=400,
                hours_old=96,
                remote_status=remote_status,
            )

            response = scraper.scrape(scraper_input=scraper_input)

            jobs_processed += len(response.jobs)
            jobs_to_save = build_jobs_to_save(response)
            if jobs_to_save:
                jobs_saved += len(jobs_to_save)
                pending_jobs.extend(jobs_to_save)
                pending_jobs = flush_pending_jobs(
                    db_session,
                    job_handler,
                    pending_jobs,
                    batch_size=batch_size,
                )

    flush_pending_jobs(
        db_session,
        job_handler,
        pending_jobs,
        batch_size=batch_size,
        force=True,
    )

    return {
        "jobs_processed": jobs_processed,
        "jobs_saved": jobs_saved,
    }


def main() -> int:
    run_sync_linkedin()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
