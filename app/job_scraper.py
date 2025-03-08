from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

from app.db.db import get_db
from app.handlers.job import JobHandler
from app.job_scrapers.linkedin import LinkedInScraper
from app.job_scrapers.scraper import (
    JobPost,
    JobType,
    RemoteStatus,
    ScraperInput,
)
from app.models.job import JobCreate
from app.utils.logging import LoggerFactory, LogLevels
from config import (
    COMPANIES_TO_IGNORE,
    JOB_LOCATIONS,
    JOB_TITLES,
    linkedin_search_string,
)

# load env file
load_dotenv()
logger = LoggerFactory.get_logger("job scraper", log_level=LogLevels.DEBUG)


def save_job(job_post: JobPost) -> bool:
    for company in COMPANIES_TO_IGNORE:
        if company.lower() == job_post.company_name.lower():
            logger.info(f"Ignoring job from {job_post.company_name}")
            return False

    for job_title in JOB_TITLES:
        if job_title.lower() not in job_post.title.lower():
            logger.info(f"Ignoring job with title {job_post.title}")
            return False
    return True


scraper = LinkedInScraper()

with next(get_db()) as db_session:
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
                hours_old=72,
                remote_status=remote_status,
            )

            response = scraper.scrape(scraper_input=scraper_input)

            job_handler = JobHandler(db_session)
            for job_post in response.jobs:
                if save_job(job_post):
                    job = JobCreate(
                        title=job_post.title,
                        company=job_post.company_name,
                        country=job_post.location.country,
                        city=job_post.location.city,
                        linkedin_url=job_post.job_url,
                        listing_date=job_post.date_posted,
                        listing_remote=job_post.remote_status,
                    )
                    try:
                        job_handler.create(job)
                    except IntegrityError:
                        logger.warning(
                            f"Duplicate job found and skipped: "
                            f"{job.title} at {job.company}"
                        )
                        job_handler.db_session.rollback()
                        continue
