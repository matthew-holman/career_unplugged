from dataclasses import dataclass

from sqlalchemy import delete
from sqlmodel import Session, col, select

from app.models.job_tag import JobTag


@dataclass
class JobTagHandler:
    db_session: Session

    def replace_tags(self, job_id: int, tags: list[JobTag]) -> None:
        """Delete all existing tags for a job and insert the new set. Flushes, does not commit."""
        self.db_session.exec(delete(JobTag).where(col(JobTag.job_id) == job_id))
        for tag in tags:
            self.db_session.add(tag)
        self.db_session.flush()

    def get_tags_for_jobs(self, job_ids: list[int]) -> list[JobTag]:
        """Batch-load tags for a list of job IDs in a single query."""
        if not job_ids:
            return []
        return list(
            self.db_session.exec(
                select(JobTag).where(col(JobTag.job_id).in_(job_ids))
            ).all()
        )
