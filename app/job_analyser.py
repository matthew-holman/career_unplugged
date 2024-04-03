import re

from app.db.db import get_db
from app.handlers.job import JobHandler
from app.job_scrapers.utils import create_session

REMOTE_COUNTRIES = [
    "EMEA",
    "European Union",
    "European Economic Area",
    "Sweden",
]

REMOTE_REG_EX_PATTERNS = [
    r"\sCET\s",
    "remote in eu",
    "distributed",
    r"remote[-\s]first",
    r"remote[-\s]friendly",
]

with next(get_db()) as db_session:
    job_handler = JobHandler(db_session)
    jobs = job_handler.get_unanalysed()

    session = create_session(is_tls=False, has_retry=True, delay=5)
    for job in jobs:
        if job.country.lower() in [
            remote_country.lower() for remote_country in REMOTE_COUNTRIES
        ]:
            job_handler.set_sweden_remote(job)
            continue

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
                job_handler.set_sweden_remote(job)
                continue

        job_handler.set_analysed(job)
