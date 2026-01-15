from time import sleep

from dotenv import load_dotenv
from sqlmodel import Session

from app.db.db import get_db
from app.handlers.career_page import CareerPageHandler
from app.handlers.job import JobHandler
from app.job_scrapers.ats_scraper_factory import AtsScraperFactory
from app.job_scrapers.linkedin import LinkedInScraper
from app.job_scrapers.scraper import (
    JobPost,
    JobResponse,
    JobType,
    RemoteStatus,
    ScraperInput,
)
from app.log import Log
from app.models.job import Job, JobCreate
from app.search_profile import (
    COMPANIES_TO_IGNORE,
    JOB_LOCATIONS,
    JOB_TITLES,
    linkedin_search_string,
)
from app.settings import settings
from app.utils.locations.europe_filter import EuropeFilter
from app.utils.locations.remote_filter import RemoteFilter


def should_save_job(job_post: JobPost) -> bool:
    for company in COMPANIES_TO_IGNORE:
        if job_post.company_name and company.lower() == job_post.company_name.lower():
            Log.info(f"Ignoring job from {job_post.company_name}")
            return False

    for job_title in JOB_TITLES:
        if job_title.lower() in job_post.title.lower():
            Log.info(f"Adding job {job_post.title} from {job_post.company_name}")
            return True

    Log.info(f"Ignoring job with title {job_post.title} from {job_post.company_name}")
    return False


def build_jobs_to_save(response: JobResponse) -> list[Job]:
    jobs: list[Job] = []
    for job_post in response.jobs:
        country = job_post.location.country if job_post.location else None

        if country:
            if not (
                EuropeFilter.is_european(country) or RemoteFilter.is_remote(country)
            ):
                Log.info(
                    f"Skipping non-European job: "
                    f"{job_post.title} at {job_post.company_name} "
                    f"(country='{country}', source='{job_post.source}')"
                )
                continue

        if should_save_job(job_post):
            job = JobCreate(
                title=job_post.title,
                company=job_post.company_name,
                country=job_post.location.country if job_post.location else None,
                city=job_post.location.city if job_post.location else None,
                source_url=job_post.job_url,
                listing_date=job_post.listing_date or job_post.date_posted,
                listing_remote=job_post.remote_status,
                source=job_post.source,
            )
            jobs.append(Job.model_validate(job))

    return jobs


def _flush_pending_jobs(
    db_session: Session,
    job_handler: JobHandler,
    pending_jobs: list[Job],
    *,
    batch_size: int,
    force: bool = False,
) -> list[Job]:
    if not pending_jobs:
        return []
    if not force and len(pending_jobs) < batch_size:
        return pending_jobs

    try:
        job_handler.save_all(pending_jobs)
        db_session.commit()
        return []
    except Exception as exc:
        db_session.rollback()
        Log.warning(f"Failed to persist jobs batch: {exc}")
        return []


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
                pending_jobs = _flush_pending_jobs(
                    db_session,
                    job_handler,
                    pending_jobs,
                    batch_size=batch_size,
                )

    _flush_pending_jobs(
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
    jobs_processed = 0
    jobs_saved = 0

    page_handler = CareerPageHandler(db_session)
    career_pages = page_handler.get_all()

    for page in career_pages:
        Log.info(f"Processing {page.company_name or page.url}")
        ats_scraper = AtsScraperFactory.get_ats_scraper(page)
        if not ats_scraper:
            Log.warning(f"No supported ATS parser for {page.url}")
            continue

        # I don't want to be blocked or limited.
        sleep(settings.ATS_SCRAPER_DELAY_SECONDS)
        response = ats_scraper.scrape()
        jobs_processed += len(response.jobs)
        jobs_to_save = build_jobs_to_save(response)
        if jobs_to_save:
            jobs_saved += len(jobs_to_save)
            pending_jobs.extend(jobs_to_save)
            pending_jobs = _flush_pending_jobs(
                db_session,
                job_handler,
                pending_jobs,
                batch_size=batch_size,
            )

    _flush_pending_jobs(
        db_session,
        job_handler,
        pending_jobs,
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
