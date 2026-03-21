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

ATS_JOB_UPSERT_CONSTRAINT = "job_ats_source_url_key"
LINKEDIN_JOB_UPSERT_CONSTRAINT = "job_linkedin_source_url_key"
ATS_JOB_UPSERT_EXCLUDE = {
    "id",
    "created_at",
    "updated_at",
    "deleted_at",
    "analysed",
    "linkedin_source_url",
}
LINKEDIN_JOB_UPSERT_EXCLUDE = {
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
        if job.ats_source_url:
            constraint = ATS_JOB_UPSERT_CONSTRAINT
            exclude = ATS_JOB_UPSERT_EXCLUDE
        else:
            constraint = LINKEDIN_JOB_UPSERT_CONSTRAINT
            exclude = LINKEDIN_JOB_UPSERT_EXCLUDE
        upsert(
            model=Job,
            db_session=self.db_session,
            constraint=constraint,
            data_iter=[job],
            exclude_columns=exclude,
        )
        self.db_session.flush()

    def save_all(self, jobs: list[Job]) -> None:
        if not jobs:
            return

        ats_deduped: dict[str, Job] = {}
        linkedin_deduped: dict[str, Job] = {}
        for job in jobs:
            if job.ats_source_url:
                ats_deduped[job.ats_source_url] = job
            elif job.linkedin_source_url:
                linkedin_deduped[job.linkedin_source_url] = job

        if ats_deduped:
            upsert(
                model=Job,
                db_session=self.db_session,
                constraint=ATS_JOB_UPSERT_CONSTRAINT,
                data_iter=list(ats_deduped.values()),
                exclude_columns=ATS_JOB_UPSERT_EXCLUDE,
            )
        if linkedin_deduped:
            upsert(
                model=Job,
                db_session=self.db_session,
                constraint=LINKEDIN_JOB_UPSERT_CONSTRAINT,
                data_iter=list(linkedin_deduped.values()),
                exclude_columns=LINKEDIN_JOB_UPSERT_EXCLUDE,
            )
        self.db_session.flush()

    def get_by_ats_source_url(self, url: str) -> Optional[Job]:
        return self.db_session.exec(
            select(Job).where(Job.ats_source_url == url)
        ).first()

    def merge_linkedin_into_ats(self, linkedin_job: Job, ats_job: Job) -> None:
        """Merge a LinkedIn job duplicate into its canonical ATS job record.

        Copies the linkedin_source_url onto the ATS job, transfers any UserJob
        activity records (OR-ing applied/ignored flags), then soft-deletes the
        LinkedIn job so it is not processed again.
        """
        # Fetch UserJob records first (before any mutations) to avoid autoflush
        # interference while both job rows still hold the same linkedin_source_url.
        linkedin_user_jobs = self.db_session.exec(
            select(UserJob).where(UserJob.job_id == linkedin_job.id)  # type: ignore[arg-type]
        ).all()

        existing_ats_ujs = {
            uj.user_id: uj
            for uj in self.db_session.exec(
                select(UserJob).where(UserJob.job_id == ats_job.id)  # type: ignore[arg-type]
            ).all()
        }

        # Step 1: Release the linkedin_source_url from the LinkedIn job first.
        # This flush clears the value in the DB so the next flush can set it
        # on the ATS job without a transient unique constraint violation.
        linkedin_url = linkedin_job.linkedin_source_url
        linkedin_job.linkedin_source_url = None
        self.db_session.add(linkedin_job)
        self.db_session.flush()

        # Step 2: Transfer the URL, activity records, and soft-delete.
        ats_job.linkedin_source_url = linkedin_url

        for linkedin_uj in linkedin_user_jobs:
            existing_ats_uj = existing_ats_ujs.get(linkedin_uj.user_id)
            if existing_ats_uj:
                existing_ats_uj.applied = existing_ats_uj.applied or linkedin_uj.applied
                existing_ats_uj.ignored = existing_ats_uj.ignored or linkedin_uj.ignored
                self.db_session.add(existing_ats_uj)
            else:
                self.db_session.add(
                    UserJob(
                        user_id=linkedin_uj.user_id,
                        job_id=ats_job.id,
                        applied=linkedin_uj.applied,
                        ignored=linkedin_uj.ignored,
                    )
                )

        linkedin_job.delete()
        self.db_session.add(linkedin_job)
        self.db_session.add(ats_job)
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
        if filters.min_remote_score is not None:
            query = query.where(Job.remote_score >= filters.min_remote_score)

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
        if filters.min_remote_score is not None:
            query = query.where(Job.remote_score >= filters.min_remote_score)

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
