from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
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
from app.models.job import JobCreate
from app.utils.europe_filter import EuropeFilter
from app.utils.log_wrapper import LoggerFactory, LogLevels
from config import (
    COMPANIES_TO_IGNORE,
    JOB_LOCATIONS,
    JOB_TITLES,
    linkedin_search_string,
)

# load env file
load_dotenv()
logger = LoggerFactory.get_logger("job scraper", log_level=LogLevels.DEBUG)


def should_save_job(job_post: JobPost) -> bool:
    for company in COMPANIES_TO_IGNORE:
        if job_post.company_name and company.lower() == job_post.company_name.lower():
            logger.info(f"Ignoring job from {job_post.company_name}")
            return False

    for job_title in JOB_TITLES:
        if job_title.lower() in job_post.title.lower():
            logger.info(f"Adding job {job_post.title} from {job_post.company_name}")
            return True

    logger.info(
        f"Ignoring job with title {job_post.title} from {job_post.company_name}"
    )
    return False


scraper = LinkedInScraper()


def persist_job_response(
    response: JobResponse, db_session: Session, job_location: str = "Not Sure"
):
    job_handler = JobHandler(db_session)
    for job_post in response.jobs:
        country = job_post.location.country if job_post.location else None

        if country and not EuropeFilter.is_european(country):
            logger.info(
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
                listing_date=job_post.date_posted,
                listing_remote=job_post.remote_status,
                source=job_post.source,
            )
            try:
                job_handler.create(job)
            except IntegrityError:
                logger.warning(
                    f"Duplicate job found and skipped: " f"{job.title} at {job.company}"
                )
                job_handler.db_session.rollback()
                continue


def run_linkedin_scraper(db_session: Session):
    for job_location in JOB_LOCATIONS:
        logger.info(f"Scraping jobs for {job_location.location}")

        remote_statuses = [RemoteStatus.ONSITE, RemoteStatus.HYBRID]
        if job_location.remote:
            remote_statuses = [RemoteStatus.REMOTE]

        for remote_status in remote_statuses:
            logger.info(f"Scraping with remote status {remote_status.name}")

            scraper_input = ScraperInput(
                search_term=linkedin_search_string(),
                location=job_location.location,
                job_type=JobType.FULL_TIME,
                results_wanted=400,
                hours_old=96,
                remote_status=remote_status,
            )

            response = scraper.scrape(scraper_input=scraper_input)

            persist_job_response(response, db_session, job_location)


def run_ats_scrapers(db_session: Session):
    page_handler = CareerPageHandler(db_session)
    career_pages = page_handler.get_all()

    for page in career_pages:
        logger.info(f"Processing {page.company_name or page.url}")
        ats_scraper = AtsScraperFactory.get_parser(page)
        if not ats_scraper:
            logger.warning(f"No supported ATS parser for {page.url}")
            continue

        response = ats_scraper.scrape()
        persist_job_response(response, db_session)


def main():
    with next(get_db()) as db_session:
        # run_linkedin_scraper(db_session)
        run_ats_scrapers(db_session)


if __name__ == "__main__":
    main()
