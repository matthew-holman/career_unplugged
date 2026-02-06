from datetime import datetime
from time import sleep

from dotenv import load_dotenv
from sqlmodel import Session

from app.db.db import get_db
from app.handlers.career_page import CareerPageHandler
from app.handlers.job import JobHandler
from app.job_scrapers.ats_scraper_factory import (
    AtsScraperFactory,
    CareerPageDeactivatedError,
)
from app.job_scrapers.linkedin import LinkedInScraper
from app.job_scrapers.scraper import JobType, RemoteStatus, ScraperInput
from app.log import Log
from app.models.career_page import CareerPage
from app.models.job import Job
from app.search_profile import JOB_LOCATIONS, linkedin_search_string
from app.settings import settings
from app.workers.sync_common import (
    build_jobs_to_save,
    flush_pending_jobs,
    flush_pending_pages,
)


def run_linkedin_scraper(db_session: Session, scraper: LinkedInScraper):
    job_handler = JobHandler(db_session)
    batch_size = settings.DB_BATCH_SIZE
    pending_jobs: list[Job] = []
    jobs_processed = 0
    jobs_saved = 0

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
    Log.info(
        f"LinkedIn scrape processed {jobs_processed} jobs, " f"saved {jobs_saved} jobs."
    )


def run_ats_scrapers(db_session: Session):
    job_handler = JobHandler(db_session)
    batch_size = settings.DB_BATCH_SIZE
    pending_jobs: list[Job] = []
    pending_pages: list[CareerPage] = []
    jobs_processed = 0
    jobs_saved = 0

    page_handler = CareerPageHandler(db_session)
    career_pages = page_handler.get_all_active()

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
            Log.warning(
                f"{AtsScraperFactory.__name__}: deactivated career page {page.url} "
                f"with status {exc.status_code}"
            )
            continue
        except KeyboardInterrupt:
            Log.error(f"KeyboardInterrupt while fetching: {page.url}")
            raise

        if not ats_scraper:
            Log.warning(f"No supported ATS parser for {page.url}")
            continue

        # I don't want to be blocked or limited.
        sleep(settings.ATS_SCRAPER_DELAY_SECONDS)
        response = ats_scraper.scrape()
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

        page.last_synced_at = datetime.utcnow()
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
    Log.info(f"ATS scrape processed {jobs_processed} jobs, saved {jobs_saved} jobs.")


def main() -> int:
    load_dotenv()
    Log.setup()
    scraper = LinkedInScraper()

    with next(get_db()) as db_session:
        run_linkedin_scraper(db_session, scraper)
        run_ats_scrapers(db_session)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
