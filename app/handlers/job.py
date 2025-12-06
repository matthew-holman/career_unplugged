from dataclasses import dataclass
from typing import List, Optional

from sqlmodel import Session, select

from app.models.job import Job, JobCreate, JobRead


@dataclass
class JobHandler:
    db_session: Session

    def get(self, job_id: int) -> Optional[Job]:
        statement = select(Job).where(Job.id == job_id)
        job = self.db_session.exec(statement).first()
        return job

    def get_unanalysed(self) -> List[Job]:
        statement = select(Job).where(Job.analysed == False)  # noqa
        jobs = self.db_session.exec(statement).all()
        return jobs

    def create(self, job: JobCreate) -> JobRead:
        validated_job = Job.model_validate(job)
        self.db_session.add(validated_job)
        self.db_session.commit()
        self.db_session.refresh(validated_job)
        return JobRead.from_orm(validated_job)

    def set_true_remote(self, job: Job, flag_reason: str) -> JobRead:
        job.true_remote = True
        job.analysed = True
        job.remote_flag_reason = flag_reason
        self.db_session.add(job)
        self.db_session.commit()
        self.db_session.refresh(job)
        return JobRead.from_orm(job)

    def set_positive_match(self, job: Job) -> JobRead:
        job.positive_keyword_match = True
        job.analysed = True
        self.db_session.add(job)
        self.db_session.commit()
        self.db_session.refresh(job)
        return JobRead.from_orm(job)

    def set_negative_match(self, job: Job) -> JobRead:
        job.negative_keyword_match = True
        job.analysed = True
        self.db_session.add(job)
        self.db_session.commit()
        self.db_session.refresh(job)
        return JobRead.from_orm(job)

    def set_analysed(self, job: Job) -> JobRead:
        job.analysed = True
        self.db_session.add(job)
        self.db_session.commit()
        self.db_session.refresh(job)
        return JobRead.from_orm(job)
