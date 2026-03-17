import re

from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup

from app.db.db import get_db
from app.handlers.career_page import CareerPageHandler
from app.handlers.job import JobHandler
from app.job_analysis import DescriptionExtractorFactory
from app.job_analysis.description_extractors.linkedin import (
    extract_apply_url_from_html,
)
from app.job_scrapers.scraper import RemoteStatus, Source
from app.job_scrapers.utils import create_session
from app.log import Log
from app.models import Job
from app.models.career_page import CareerPageCreate
from app.search_profile import NEGATIVE_MATCH_KEYWORDS, POSITIVE_MATCH_KEYWORDS
from app.settings import settings
from app.utils.ats_discovery import (
    discover_career_page,
    extract_slug_from_career_page_url,
)

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
    r"\\b(fully[-\s]?(distributed|remote))\b",
    r"\b(across\s(EMEA|EU|timezones))\b",
    r"\b(flexible\slocation)\b",
    r"\b(work\sanywhere\s(in|across)\sEurope)\b",
    r"\b(remote(ly)?\s(within|from|across)?\s(Sweden|Europe|EU|EMEA))\b",
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
    r"\b(remote(ly)?\s+in\s+(Europe|EMEA|Sweden))\b",
]

TRUE_REMOTE_COUNTRIES = [
    "EMEA",
    "European",
    "European Union",
    "European Economic Area",
    "Europe",
]


def _mark_true_remote_jobs(jobs) -> list:
    updated_jobs = []
    for job in jobs:
        if job.country is not None and job.country.lower() in [
            remote_country.lower() for remote_country in TRUE_REMOTE_COUNTRIES
        ]:
            job.mark_true_remote("True Remote Location")
            Log.info(
                f"Job {job.title} at {job.company} with country {job.country} is EU remote."
            )
            updated_jobs.append(job)
            continue

        if (
            job.country is not None
            and "sweden" in job.country.lower()
            and job.listing_remote == RemoteStatus.REMOTE
        ):
            job.mark_true_remote("Sweden Remote")
            Log.info(
                f"Job {job.title} at {job.company} with country {job.country} is Sweden remote."
            )
            updated_jobs.append(job)
    return updated_jobs


def _fetch_job_page(session, job) -> str | None:
    url = job.ats_source_url or job.linkedin_source_url
    response = session.get(url)
    if response.status_code != 200:
        Log.warning(
            f"Failed to fetch description for {job.source} job {job.id} "
            f"({url}): {response.status_code}"
        )
        return None
    return response.text


def _extract_job_description(job_page_html: str, job: Job) -> str | None:
    soup = BeautifulSoup(job_page_html, "html.parser")

    extractor = DescriptionExtractorFactory.get_for_source(job.source)
    if not extractor:
        Log.warning(
            f"Failed to load description extractor for source:{job.source} and job:{job.id} "
        )
        return None

    return extractor.extract_description(soup, job) or ""


def _normalize_ats_url(url: str) -> str:
    """Strip query params and fragment — LinkedIn adds tracking params to ATS URLs."""
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))


def _discover_career_page_from_linkedin(
    job,
    external_apply_url: str,
    career_page_handler: CareerPageHandler,
) -> None:
    discovery = discover_career_page(external_apply_url)
    if not discovery:
        Log.info(
            f"LinkedIn job url: {external_apply_url}, doesn't match existing ats scrapers"
        )
        return

    canonical_url = discovery.url
    slug = extract_slug_from_career_page_url(canonical_url)
    # Prefer ATS slugs to keep naming consistent across discovered pages.
    company_name = slug or job.company

    _, created = career_page_handler.upsert_discovered(
        CareerPageCreate(company_name=company_name, url=canonical_url)
    )
    if created:
        provider = discovery.source.value
        Log.info(
            f"Discovered {provider} career page from LinkedIn job: {canonical_url}"
        )


def _update_ats_url_for_linkedin_job(
    job: Job, external_url: str, job_handler: JobHandler
) -> None:
    normalized = _normalize_ats_url(external_url)
    existing_ats_job = job_handler.get_by_ats_source_url(normalized)
    if existing_ats_job:
        Log.info(
            f"Merging LinkedIn job {job.id} into ATS job "
            f"{existing_ats_job.id} ({normalized})"
        )
        job_handler.merge_linkedin_into_ats(job, existing_ats_job)
    else:
        job.ats_source_url = normalized
        Log.info(f"Set ats_source_url={normalized} on LinkedIn job {job.id}")


def _apply_keyword_analysis(job: Job, text: str) -> None:
    for pattern in REMOTE_REG_EX_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            job.mark_true_remote(pattern)
            Log.info(
                f"Job {job.title} at {job.company} has match with {pattern} in job description text."
            )
            break

    for pattern in POSITIVE_MATCH_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            job.mark_positive_match()
            break

    for pattern in NEGATIVE_MATCH_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            job.mark_negative_match()
            break


def _apply_description_analysis(
    job: Job, session, career_page_handler: CareerPageHandler, job_handler: JobHandler
) -> None:
    job_page_html = _fetch_job_page(session, job)
    if not job_page_html:
        job.mark_analysed()
        return

    if job.source == Source.LINKEDIN:
        external_url = extract_apply_url_from_html(job_page_html)
        if external_url:
            _discover_career_page_from_linkedin(job, external_url, career_page_handler)
            _update_ats_url_for_linkedin_job(job, external_url, job_handler)

    job_description_text = _extract_job_description(job_page_html, job)
    if job_description_text is None:
        job.mark_analysed()
        return

    _apply_keyword_analysis(job, job_description_text)
    job.mark_analysed()


def _flush_pending_jobs(
    db_session,
    job_handler: JobHandler,
    pending_jobs: list,
    *,
    batch_size: int,
    force: bool = False,
) -> list:
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
        Log.warning(f"Failed to persist analysis batch: {exc}")
        return []


def main() -> int:
    return run_analyser()


def run_analyser() -> int:
    with next(get_db()) as db_session:
        job_handler = JobHandler(db_session)
        career_page_handler = CareerPageHandler(db_session)
        jobs = job_handler.get_pending_analysis()
        batch_size = settings.DB_BATCH_SIZE
        pending_jobs: list = []
        jobs_processed = 0
        jobs_saved = 0

        updated_jobs = _mark_true_remote_jobs(jobs)
        if updated_jobs:
            jobs_saved += len(updated_jobs)
            pending_jobs.extend(updated_jobs)
            pending_jobs = _flush_pending_jobs(
                db_session,
                job_handler,
                pending_jobs,
                batch_size=batch_size,
            )

        session = create_session(is_tls=False, has_retry=True, delay=15)
        for job in jobs:
            jobs_processed += 1
            _apply_description_analysis(job, session, career_page_handler, job_handler)
            if job.deleted_at is None:
                jobs_saved += 1
                pending_jobs.append(job)
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
        Log.info(f"Analysis processed {jobs_processed} jobs, saved {jobs_saved} jobs.")
    return 0


if __name__ == "__main__":
    Log.setup()
    raise SystemExit(main())
