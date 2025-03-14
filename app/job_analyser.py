import re

from app.db.db import get_db
from app.handlers.job import JobHandler
from app.job_scrapers.utils import create_session
from app.utils.logging import LoggerFactory, LogLevels
from config import NEGATIVE_MATCH_KEYWORDS, POSITIVE_MATCH_KEYWORDS

REMOTE_REG_EX_PATTERNS = [
    r"\sCET\s",
    "remote in eu",
    r"remote[-\s]first",
    r"remote[-\s]friendly",
    r"100%[-\s]remote",
]

TRUE_REMOTE_COUNTRIES = [
    "EMEA",
    "European Union",
    "European Economic Area",
]

logger = LoggerFactory.get_logger("job scraper", log_level=LogLevels.DEBUG)

with next(get_db()) as db_session:
    job_handler = JobHandler(db_session)
    jobs = job_handler.get_unanalysed()

    for job in jobs:
        if job.country.lower() in [
            remote_country.lower() for remote_country in TRUE_REMOTE_COUNTRIES
        ]:
            job_handler.set_true_remote(job)
            logger.info(f"Job {job.title} at {job.company} with country {job.country} is EU remote.")
            continue

    session = create_session(is_tls=False, has_retry=True, delay=15)
    for job in jobs:
        job_description = session.get(job.linkedin_url)
        if job_description.status_code != 200:
            raise Exception(
                "Got an error response, status code: {}".format(
                    job_description.status_code
                )
            )

        job_description_text = job_description.content.decode("utf-8")

        for pattern in REMOTE_REG_EX_PATTERNS:
            match = re.search(pattern, job_description_text, re.IGNORECASE)
            if match is not None:
                job_handler.set_true_remote(job)
                logger.info(f"Job {job.title} at {job.company} has match with {pattern} in job description text.")
                break

        for pattern in POSITIVE_MATCH_KEYWORDS:
            match = re.search(pattern, job_description_text, re.IGNORECASE)
            if match is not None:
                job_handler.set_positive_match(job)
                break

        for pattern in NEGATIVE_MATCH_KEYWORDS:
            match = re.search(pattern, job_description_text, re.IGNORECASE)
            if match is not None:
                job_handler.set_negative_match(job)
                break

        job_handler.set_analysed(job)
