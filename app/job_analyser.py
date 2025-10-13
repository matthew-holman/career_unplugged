import re

from bs4 import BeautifulSoup

from app.db.db import get_db
from app.handlers.job import JobHandler
from app.job_scrapers.scraper import RemoteStatus
from app.job_scrapers.utils import create_session
from app.utils.log_wrapper import LoggerFactory, LogLevels
from config import NEGATIVE_MATCH_KEYWORDS, POSITIVE_MATCH_KEYWORDS

REMOTE_REG_EX_PATTERNS = [
    r"\sCET\s",
    "remote in eu",
    r"remote[-\s]first",
    r"remote[-\s]friendly",
    r"100%[-\s]remote",
    r"Western[-\s]European[-\s]timezones",
    r"global[-\s]payroll[-\s]service[-\s]provider"
    r"Employer[-\s]of[-\s]Record"
    r"\b(remote[-\s]?first)\b",
    r"\b(remote[-\s]?friendly)\b",
    r"\b(100%[-\s]?remote)\b",
    r"\b(remote[-\s]?only)\b",
    r"\b(full[-\s]?remote)\b",
    r"\b(work\sfrom\sanywhere)\b",
    r"\b(async[-\s]?team)\b",
    r"\b(we\soperate\sasync)\b",
    r"\b(fully[-\s]?distributed)\b",
    r"\b(across\s(Europe|EMEA|EU|timezones))\b",
    r"\b(flexible\slocation)\b",
    r"\b(work\sanywhere\s(in|across)\sEurope)\b",
    r"\b(remote\s(within|from)?\s(Sweden|Europe|EU|EMEA))\b",
    r"\b(no\srelocation\sneeded)\b",
    r"\b(location[-\s]?agnostic)\b"
    r"\b(distributed[-\s]?team)\b",
    r"\b(CET|CEST|Central European (Standard|Summer)? Time)\b",
    r"\b(UTC[\s±+-]?\d{1,2})\b",  # e.g. UTC+1, UTC -2
    r"\b(European\s+timezones?)\b",
    r"\b(within\s+([±+−-]?\s?\d{1,2}\s?(hrs?|hours?)?)\s+of\s+(CET|UTC))\b",
    r"\b(time[-\s]?zone:\s?(CET|UTC[\s+-]?\d))\b",
    r"\b(\bwithin\b\s?\d{1,2}[-\s]?(hrs?|hours?)\s?(of)?\s?(CET|Central European Time|UTC))",
    r"\b(based in\s+(Europe|EU|EMEA)[\s,]+but\s+open\s+to\s+remote)\b",
    r"\b(remote[-\s]work\s+(within|across)\s+(Europe|EU|EMEA))\b",
    r"\b(work\sfrom\sanywhere\s(in|within)\s(Europe|EMEA))\b",
    r"\b(remote\s+in\s+(Europe|EMEA|Sweden))\b",
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

        if "sweden" in job.country.lower() and job.listing_remote == RemoteStatus.REMOTE:
            job_handler.set_true_remote(job)
            logger.info(f"Job {job.title} at {job.company} with country {job.country} is Sweden remote.")
            continue

    session = create_session(is_tls=False, has_retry=True, delay=15)
    for job in jobs:
        job_description_response = session.get(job.linkedin_url)
        if job_description_response.status_code != 200:
            raise Exception(
                "Got an error response, status code: {}".format(
                    job_description_response.status_code
                )
            )

        soup = BeautifulSoup(job_description_response.text, "html.parser")
        description_section = soup.find("section", class_="core-section-container my-3 description")

        if description_section:
            job_description_text = description_section.decode_contents()
        else:
            job_description_text = ""

        # job_description_text = job_description.content.decode("utf-8")

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
