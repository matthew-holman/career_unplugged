from dataclasses import dataclass
from typing import Optional, Sequence

from sqlmodel import Session, select

from app.db.db import upsert
from app.models.job import Job

JOB_UPSERT_CONSTRAINT = "job_source_url_key"
JOB_UPSERT_EXCLUDE = {"id", "created_at", "updated_at", "deleted_at"}


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
