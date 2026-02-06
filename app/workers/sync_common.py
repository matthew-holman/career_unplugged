from __future__ import annotations

from collections import Counter

from sqlmodel import Session

from app.handlers.job import JobHandler
from app.job_scrapers.scraper import JobPost, JobResponse
from app.log import Log
from app.models.career_page import CareerPage
from app.models.job import Job, JobCreate
from app.search_profile import COMPANIES_TO_IGNORE, JOB_TITLES
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


def build_jobs_to_save(
    response: JobResponse, *, career_page_id: int | None = None
) -> list[Job]:
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
                career_page_id=career_page_id,
            )
            jobs.append(Job.model_validate(job))

    return jobs


def flush_pending_jobs(
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

    # Deduplicate within the batch to avoid:
    # psycopg2.errors.CardinalityViolation: ON CONFLICT DO UPDATE command cannot affect row a second time
    #
    # "Last write wins" is usually the least surprising in scraping pipelines,
    # because later passes may have richer/more-correct fields.
    jobs_by_source_url: dict[str, Job] = {}
    for job in pending_jobs:
        # Defensive: ignore impossible/invalid entries rather than crashing the whole batch
        if not job.source_url:
            continue
        jobs_by_source_url[job.source_url] = job

    deduped_jobs = list(jobs_by_source_url.values())

    # Optional logging to prove you fixed the problem (and to find upstream dup sources)
    if len(deduped_jobs) != len(pending_jobs):
        source_url_counts = Counter(
            job.source_url for job in pending_jobs if job.source_url
        )
        duplicate_count = sum(1 for count in source_url_counts.values() if count > 1)
        Log.warning(
            "Deduped pending_jobs before insert: "
            f"{len(pending_jobs)} -> {len(deduped_jobs)} "
            f"({duplicate_count} duplicated source_url values)"
        )

    try:
        job_handler.save_all(deduped_jobs)
        db_session.commit()
        return []
    except Exception as exc:
        db_session.rollback()
        Log.warning(f"Failed to persist jobs batch: {exc}")
        return []


def flush_pending_pages(
    db_session: Session,
    pending_pages: list[CareerPage],
    *,
    batch_size: int,
    force: bool = False,
) -> list[CareerPage]:
    if not pending_pages:
        return []
    if not force and len(pending_pages) < batch_size:
        return pending_pages

    try:
        for page in pending_pages:
            db_session.add(page)
        db_session.commit()
        return []
    except Exception as exc:
        db_session.rollback()
        Log.warning(f"Failed to persist career pages batch: {exc}")
        return []
