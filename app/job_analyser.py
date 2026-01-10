import re

from bs4 import BeautifulSoup

from app.db.db import get_db
from app.handlers.job import JobHandler
from app.job_analysis import DescriptionExtractorFactory
from app.job_scrapers.scraper import RemoteStatus
from app.job_scrapers.utils import create_session
from app.utils.log_wrapper import LoggerFactory, LogLevels
from config import NEGATIVE_MATCH_KEYWORDS, POSITIVE_MATCH_KEYWORDS

REMOTE_REG_EX_PATTERNS = [
    r"\s(GMT|CET)\s",
    "remote in eu",
    r"Remote[-\s]first in Europe" r"remote[-\s]first",
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
    r"\b(across\s(EMEA|EU|timezones))\b",
    r"\b(flexible\slocation)\b",
    r"\b(work\sanywhere\s(in|across)\sEurope)\b",
    r"\b(remote\s(within|from)?\s(Sweden|Europe|EU|EMEA))\b",
    r"\b(no\srelocation\sneeded)\b",
    r"\b(location[-\s]?agnostic)\b" r"\b(distributed[-\s]?team)\b",
    r"\b(GMT|CET|CEST|Central European (Standard|Summer)? Time)\b",
    r"\b(UTC[\s±+-]?\d{1,2})\b",  # e.g. UTC+1, UTC -2
    r"\b(European\s+timezones?)\b",
    r"\b(within\s+([±+−-]?\s?\d{1,2}\s?(hrs?|hours?)?)\s+of\s+(GMT|CET|UTC))\b",
    r"\b(time[-\s]?zone:\s?(GMT|CET|UTC[\s+-]?\d))\b",
    r"\b(\bwithin\b\s?\d{1,2}[-\s]?(hrs?|hours?)\s?(of)?\s?(GMT|CET|Central European Time|UTC))",
    r"\b(based in\s+(Europe|EU|EMEA)[\s,]+but\s+open\s+to\s+remote)\b",
    r"\b(remote[-\s]work\s+(within|across)\s+(Europe|EU|EMEA))\b",
    r"\b(work\sfrom\sanywhere\s(in|within)\s(Europe|EMEA))\b",
    r"\b(remote\s+in\s+(Europe|EMEA|Sweden))\b",
]

TRUE_REMOTE_COUNTRIES = [
    "EMEA",
    "European",
    "European Union",
    "European Economic Area",
    "Europe",
]

logger_singleton = None


def _get_logger():
    global logger_singleton
    if logger_singleton is None:
        logger_singleton = LoggerFactory.get_logger(
            "job scraper", log_level=LogLevels.DEBUG
        )
    return logger_singleton


def main() -> int:
    logger = _get_logger()
    with next(get_db()) as db_session:
        job_handler = JobHandler(db_session)
        jobs = job_handler.get_unanalysed()

        for job in jobs:
            if job.country is not None and job.country.lower() in [
                remote_country.lower() for remote_country in TRUE_REMOTE_COUNTRIES
            ]:
                job_handler.set_true_remote(job, "True Remote Location")
                logger.info(
                    f"Job {job.title} at {job.company} with country {job.country} is EU remote."
                )
                continue

            if (
                job.country is not None
                and "sweden" in job.country.lower()
                and job.listing_remote == RemoteStatus.REMOTE
            ):
                job_handler.set_true_remote(job, "Sweden Remote")
                logger.info(
                    f"Job {job.title} at {job.company} with country {job.country} is Sweden remote."
                )
                continue

        session = create_session(is_tls=False, has_retry=True, delay=15)
        for job in jobs:
            job_description_response = session.get(job.source_url)
            if job_description_response.status_code != 200:
                logger.warning(
                    f"Failed to fetch description for {job.source} job {job.id} "
                    f"({job.source_url}): {job_description_response.status_code}"
                )
                job_handler.set_analysed(job)
                continue

            soup = BeautifulSoup(job_description_response.text, "html.parser")

            extractor = DescriptionExtractorFactory.get_for_source(job.source)
            if not extractor:
                logger.warning(
                    f"Failed to load description extractor for source:{job.source} and job:{job.id} "
                )
                continue

            job_description_text = extractor.extract_description(soup) or ""

            for pattern in REMOTE_REG_EX_PATTERNS:
                match = re.search(pattern, job_description_text, re.IGNORECASE)
                if match is not None:
                    job_handler.set_true_remote(job, pattern)
                    logger.info(
                        f"Job {job.title} at {job.company} has match with {pattern} in job description text."
                    )
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
