from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func
from sqlmodel import Session, col, select

from app.handlers.job import eligible_remote_expr
from app.job_scrapers.scraper import RemoteStatus
from app.models.job import Job
from app.models.user import User
from app.models.user_job import UserJob
from app.schemas.dashboard import JobSummary


@dataclass
class DashboardHandler:
    db_session: Session

    def get_jobs_summary(self, current_user: User) -> JobSummary:
        source_counts = self.db_session.exec(
            select(Job.source, func.count()).group_by(Job.source)
        ).all()
        country_counts = self.db_session.exec(
            select(Job.country, func.count()).group_by(Job.country)
        ).all()
        remote_counts = self.db_session.exec(
            select(Job.listing_remote, func.count()).group_by(Job.listing_remote)
        ).all()

        counts_by_source = {
            (source.value if source else "unknown"): count
            for source, count in source_counts
        }
        counts_by_country = {
            (country if country else "unknown"): count
            for country, count in country_counts
        }
        counts_by_remote_status = {
            (
                status.value
                if isinstance(status, RemoteStatus)
                else (status if status else "unknown")
            ): count
            for status, count in remote_counts
        }

        to_review = self.db_session.exec(
            select(func.count()).where(
                and_(
                    col(UserJob.user_id) == current_user.id,
                    col(UserJob.applied).is_(True),
                )
            )
        ).one()
        eu_remote = self.db_session.exec(
            select(func.count()).where(eligible_remote_expr())
        ).one()
        sweden = self.db_session.exec(
            select(func.count()).where(func.lower(col(Job.country)) == "sweden")
        ).one()
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        new7d = self.db_session.exec(
            select(func.count()).where(Job.created_at >= cutoff)
        ).one()
        return JobSummary(
            counts_by_source=counts_by_source,
            counts_by_country=counts_by_country,
            counts_by_remote_status=counts_by_remote_status,
            to_review=to_review,
            eu_remote=eu_remote,
            sweden=sweden,
            new7d=new7d,
        )
