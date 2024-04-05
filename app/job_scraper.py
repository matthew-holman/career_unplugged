import logging

from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

from app.db.db import get_db
from app.handlers.job import JobHandler
from app.job_scrapers.linkedin import LinkedInScraper
from app.job_scrapers.scraper import JobPost, JobType, ScraperInput
from app.models.job import JobCreate
from config import JOB_LOCATIONS, JOB_TITLES, linkedin_search_string

# load env file
load_dotenv()


def save_job(job_post: JobPost) -> bool:
    for job_title in JOB_TITLES:
        if job_title in job_post.title.lower():
            return True
    return False


scraper = LinkedInScraper()

with next(get_db()) as db_session:
    for job_location in JOB_LOCATIONS:
        scraper_input = ScraperInput(
            search_term=linkedin_search_string(),
            location=job_location,
            job_type=JobType.FULL_TIME,
            results_wanted=10,
            hours_old=24,
            is_remote=True,
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
                )
                try:
                    job_handler.create(job)
                except IntegrityError:
                    logging.warning(
                        f"Duplicate job found and skipped: "
                        f"{job.title} at {job.company}"
                    )
                    job_handler.db_session.rollback()
                    continue
