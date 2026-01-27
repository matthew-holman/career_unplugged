from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from sqlalchemy import and_, func, or_
from sqlmodel import Session, col, select

from app.db.db import upsert
from app.filters.job import JobFilter
from app.job_scrapers.scraper import RemoteStatus
from app.models.job import Job, JobRead
from app.models.user_job import UserJob
from app.schemas.job import JobWithUserStateRead, UserJobStateRead, UserJobStateUpdate
from app.utils.locations.europe_filter import EuropeFilter

JOB_UPSERT_CONSTRAINT = "job_source_url_key"
JOB_UPSERT_EXCLUDE = {"id", "created_at", "updated_at", "deleted_at", "analysed"}
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
        upsert(
            model=Job,
            db_session=self.db_session,
            constraint=JOB_UPSERT_CONSTRAINT,
            data_iter=[job],
            exclude_columns=JOB_UPSERT_EXCLUDE,
        )
        self.db_session.flush()

    def save_all(self, jobs: list[Job]) -> None:
        if not jobs:
            return

        deduped: dict[tuple[str, str], Job] = {}
        for job in jobs:
            if not job.source or not job.source_url:
                continue  # or raise; depends on your invariants
            deduped[(job.source, job.source_url)] = job

        upsert(
            model=Job,
            db_session=self.db_session,
            constraint=JOB_UPSERT_CONSTRAINT,
            data_iter=list(deduped.values()),
            exclude_columns=JOB_UPSERT_EXCLUDE,
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
