from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from sqlalchemy import and_, func, or_
from sqlmodel import Session, col, select

from app.db.db import upsert
from app.filters.job import JobFilter
from app.filters.user_activity import UserActivityFilter
from app.job_scrapers.scraper import RemoteStatus
from app.models.job import Job, JobRead
from app.models.user_job import UserJob
from app.schemas.job import JobWithUserStateRead, UserJobStateRead, UserJobStateUpdate
from app.utils.locations.europe_filter import EuropeFilter

# ATS scrapers: upsert on ats_source_url, never overwrite an existing linkedin_url
ATS_UPSERT_CONSTRAINT = "job_ats_source_url_key"
ATS_UPSERT_EXCLUDE = {
    "id",
    "created_at",
    "updated_at",
    "deleted_at",
    "analysed",
    "linkedin_url",
}

# LinkedIn scraper when an ATS URL was also extracted: upsert on ats_source_url,
# and DO write linkedin_url onto the row (to link an existing ATS row to LinkedIn)
LINKEDIN_ATS_UPSERT_CONSTRAINT = "job_ats_source_url_key"
LINKEDIN_ATS_UPSERT_EXCLUDE = {
    "id",
    "created_at",
    "updated_at",
    "deleted_at",
    "analysed",
}

# LinkedIn scraper when no ATS URL was found: upsert on linkedin_url,
# and never overwrite an existing ats_source_url with NULL
LINKEDIN_ONLY_UPSERT_CONSTRAINT = "job_linkedin_url_key"
LINKEDIN_ONLY_UPSERT_EXCLUDE = {
    "id",
    "created_at",
    "updated_at",
    "deleted_at",
    "analysed",
    "ats_source_url",
}

USER_JOB_UPSERT_EXCLUDE: set[str] = set()


@dataclass
class JobHandler:
    db_session: Session

    def get(self, job_id: int) -> Optional[Job]:
        statement = select(Job).where(Job.id == job_id)
        job = self.db_session.exec(statement).first()
        return job

    def get_pending_analysis(self) -> Sequence[Job]:
        statement = select(Job).where(Job.analysed == False)  # noqa
        jobs = self.db_session.exec(statement).all()
        return jobs

    def save(self, job: Job) -> None:
        self.save_all([job])

    def save_all(self, jobs: list[Job]) -> None:
        if not jobs:
            return

        # Deduplicate within the batch: prefer ats_source_url as the canonical key
        deduped: dict[str, Job] = {}
        for job in jobs:
            key = job.ats_source_url or job.linkedin_url
            if not key:
                continue
            deduped[key] = job

        deduped_jobs = list(deduped.values())

        # Split into three groups based on source and which URLs are present:
        #
        # 1. ATS scrapers (source != LINKEDIN): always have ats_source_url, never
        #    linkedin_url — upsert on ats_source_url, preserve any existing linkedin_url.
        #
        # 2. LinkedIn scraper + ATS URL extracted: upsert on ats_source_url so the row
        #    merges with any existing ATS row, and also writes linkedin_url onto it.
        #
        # 3. LinkedIn scraper, no ATS URL found: upsert on linkedin_url, preserve any
        #    existing ats_source_url (won't be nulled out).

        ats_only = [j for j in deduped_jobs if j.ats_source_url and not j.linkedin_url]
        linkedin_with_ats = [
            j for j in deduped_jobs if j.ats_source_url and j.linkedin_url
        ]
        linkedin_only = [
            j for j in deduped_jobs if not j.ats_source_url and j.linkedin_url
        ]

        if ats_only:
            upsert(
                model=Job,
                db_session=self.db_session,
                constraint=ATS_UPSERT_CONSTRAINT,
                data_iter=ats_only,
                exclude_columns=ATS_UPSERT_EXCLUDE,
            )

        if linkedin_with_ats:
            upsert(
                model=Job,
                db_session=self.db_session,
                constraint=LINKEDIN_ATS_UPSERT_CONSTRAINT,
                data_iter=linkedin_with_ats,
                exclude_columns=LINKEDIN_ATS_UPSERT_EXCLUDE,
            )

        if linkedin_only:
            upsert(
                model=Job,
                db_session=self.db_session,
                constraint=LINKEDIN_ONLY_UPSERT_CONSTRAINT,
                data_iter=linkedin_only,
                exclude_columns=LINKEDIN_ONLY_UPSERT_EXCLUDE,
            )

        self.db_session.flush()

    def list_for_user(
        self, filters: JobFilter, user_id: int
    ) -> list[JobWithUserStateRead]:
        applied_expr = func.coalesce(UserJob.applied, False)
        ignored_expr = func.coalesce(UserJob.ignored, False)

        query = (
            select(
                Job,
                applied_expr.label("applied"),
                ignored_expr.label("ignored"),
            )
            .outerjoin(
                UserJob,
                and_(UserJob.job_id == Job.id, UserJob.user_id == user_id),  # type: ignore[arg-type]
            )
            .select_from(Job)
        )

        provided = filters.model_dump(exclude_none=True)
        filter_builders = {
            "title": lambda value: Job.title == value,
            "company": lambda value: Job.company == value,
            "country": lambda value: Job.country == value,
            "city": lambda value: Job.city == value,
            "positive_keyword_match": lambda value: (
                Job.positive_keyword_match == value
            ),
            "negative_keyword_match": lambda value: (
                Job.negative_keyword_match == value
            ),
            "true_remote": lambda value: Job.true_remote == value,
            "analysed": lambda value: Job.analysed == value,
            "listing_remote": lambda value: Job.listing_remote == value,
            "source": lambda value: Job.source == value,
            "created_at_gte": lambda value: Job.created_at >= value,
            "created_at_lte": lambda value: Job.created_at <= value,
            "listing_date_gte": lambda value: col(Job.listing_date) >= value,
            "listing_date_lte": lambda value: col(Job.listing_date) <= value,
            "applied": lambda value: applied_expr == value,
            "ignored": lambda value: ignored_expr == value,
        }

        for field_name, value in provided.items():
            builder = filter_builders.get(field_name)
            if builder is not None:
                query = query.where(builder(value))

        if filters.recent_days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=filters.recent_days)
            query = query.where(Job.created_at >= cutoff)
        if filters.eu_remote is True:
            eu_countries = sorted(EuropeFilter.EU_COUNTRIES)
            eu_match = func.lower(col(Job.country)).in_(eu_countries)
            eu_remote = or_(
                col(Job.true_remote).is_(True),
                and_(col(Job.listing_remote) == RemoteStatus.REMOTE, eu_match),
            )
            query = query.where(eu_remote)

        if "applied" not in provided and "ignored" not in provided:
            query = query.where(applied_expr.is_(False), ignored_expr.is_(False))

        results = self.db_session.exec(query).all()
        return [
            JobWithUserStateRead(
                **JobRead.model_validate(job).model_dump(),
                applied=applied,
                ignored=ignored,
            )
            for job, applied, ignored in results
        ]

    def list_user_activity(
        self, filters: UserActivityFilter, user_id: int
    ) -> list[JobWithUserStateRead]:
        applied_expr = UserJob.applied
        ignored_expr = UserJob.ignored

        query = (
            select(
                Job,
                applied_expr.label("applied"),  # type: ignore[attr-defined]
                ignored_expr.label("ignored"),  # type: ignore[attr-defined]
            )
            .join(
                UserJob,
                and_(UserJob.job_id == Job.id, UserJob.user_id == user_id),  # type: ignore[arg-type]
            )
            .select_from(Job)
        )

        provided = filters.model_dump(exclude_none=True)
        provided.pop("activity", None)
        filter_builders = {
            "title": lambda value: Job.title == value,
            "company": lambda value: Job.company == value,
            "country": lambda value: Job.country == value,
            "city": lambda value: Job.city == value,
            "positive_keyword_match": lambda value: (
                Job.positive_keyword_match == value
            ),
            "negative_keyword_match": lambda value: (
                Job.negative_keyword_match == value
            ),
            "true_remote": lambda value: Job.true_remote == value,
            "analysed": lambda value: Job.analysed == value,
            "listing_remote": lambda value: Job.listing_remote == value,
            "source": lambda value: Job.source == value,
            "created_at_gte": lambda value: Job.created_at >= value,
            "created_at_lte": lambda value: Job.created_at <= value,
            "listing_date_gte": lambda value: col(Job.listing_date) >= value,
            "listing_date_lte": lambda value: col(Job.listing_date) <= value,
            "applied": lambda value: applied_expr == value,
            "ignored": lambda value: ignored_expr == value,
        }

        for field_name, value in provided.items():
            builder = filter_builders.get(field_name)
            if builder is not None:
                query = query.where(builder(value))

        if filters.recent_days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=filters.recent_days)
            query = query.where(Job.created_at >= cutoff)
        if filters.eu_remote is True:
            eu_countries = sorted(EuropeFilter.EU_COUNTRIES)
            eu_match = func.lower(col(Job.country)).in_(eu_countries)
            eu_remote = or_(
                col(Job.true_remote).is_(True),
                and_(col(Job.listing_remote) == RemoteStatus.REMOTE, eu_match),
            )
            query = query.where(eu_remote)

        if filters.applied is None and filters.ignored is None:
            if filters.activity == "applied":
                query = query.where(applied_expr.is_(True))  # type: ignore[attr-defined]
            elif filters.activity == "ignored":
                query = query.where(ignored_expr.is_(True))  # type: ignore[attr-defined]
            else:
                query = query.where(or_(applied_expr.is_(True), ignored_expr.is_(True)))  # type: ignore[attr-defined]

        results = self.db_session.exec(query).all()
        return [
            JobWithUserStateRead(
                **JobRead.model_validate(job).model_dump(),
                applied=applied,
                ignored=ignored,
            )
            for job, applied, ignored in results
        ]

    def get_for_user(self, job_id: int, user_id: int) -> Optional[JobWithUserStateRead]:
        applied_expr = func.coalesce(UserJob.applied, False)
        ignored_expr = func.coalesce(UserJob.ignored, False)

        query = (
            select(
                Job,
                applied_expr.label("applied"),
                ignored_expr.label("ignored"),
            )
            .outerjoin(
                UserJob,
                and_(UserJob.job_id == Job.id, UserJob.user_id == user_id),  # type: ignore[arg-type]
            )
            .where(Job.id == job_id)
            .select_from(Job)
        )
        result = self.db_session.exec(query).first()
        if result is None:
            return None
        job, applied, ignored = result
        return JobWithUserStateRead(
            **JobRead.model_validate(job).model_dump(),
            applied=applied,
            ignored=ignored,
        )

    def upsert_user_job_state(
        self, user_id: int, job_id: int, state: UserJobStateUpdate
    ) -> UserJobStateRead:
        statement = select(UserJob).where(
            and_(UserJob.user_id == user_id, UserJob.job_id == job_id)  # type: ignore[arg-type]
        )
        existing = self.db_session.exec(statement).first()

        applied = (
            state.applied
            if state.applied is not None
            else (existing.applied if existing else False)
        )
        ignored = (
            state.ignored
            if state.ignored is not None
            else (existing.ignored if existing else False)
        )
        user_job = UserJob(
            user_id=user_id,
            job_id=job_id,
            applied=applied,
            ignored=ignored,
        )
        updated = upsert(
            model=UserJob,
            db_session=self.db_session,
            exclude_columns=USER_JOB_UPSERT_EXCLUDE,
            data_iter=[user_job],
            index_elements=["user_id", "job_id"],
        )[0]
        self.db_session.commit()

        return UserJobStateRead(
            user_id=updated.user_id,
            job_id=updated.job_id,
            applied=updated.applied,
            ignored=updated.ignored,
        )
