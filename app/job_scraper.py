import logging
import os

from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

from app.db.db import get_db
from app.handlers.job import JobHandler
from app.job_scrapers.linkedin import LinkedInScraper
from app.job_scrapers.scraper import JobType, ScraperInput
from app.models.job import JobCreate

# load env file
load_dotenv()

scraper_input = ScraperInput(
    site_name=["linkedin"],
    search_term=os.getenv("LINKEDIN_SEARCH_TERM"),
    location=os.getenv("LINKEDIN_SEARCH_LOCATION"),
    job_type=JobType.FULL_TIME,
    results_wanted=200,
    hours_old=24,
    is_remote=True,
)

scraper = LinkedInScraper()
response = scraper.scrape(scraper_input=scraper_input)

with next(get_db()) as db_session:
    job_handler = JobHandler(db_session)
    for job_post in response.jobs:
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
