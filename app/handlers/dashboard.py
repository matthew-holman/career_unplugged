from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_
from sqlmodel import Session, col, select

from app.job_scrapers.scraper import RemoteStatus
from app.models.job import Job
from app.models.user import User
from app.models.user_job import UserJob
from app.schemas.dashboard import JobSummary
from app.utils.locations.europe_filter import EuropeFilter


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

        eu_countries = sorted(EuropeFilter.EU_COUNTRIES)
        eu_match = func.lower(col(Job.country)).in_(eu_countries)
        eu_remote_filter = or_(
            col(Job.true_remote).is_(True),
            and_(col(Job.listing_remote) == RemoteStatus.REMOTE, eu_match),
        )

        to_review = self.db_session.exec(
            select(func.count()).where(
                and_(
                    col(UserJob.user_id) == current_user.id,
                    col(UserJob.applied).is_(True),
                )
            )
        ).one()
        eu_remote = self.db_session.exec(
            select(func.count()).where(eu_remote_filter)
        ).one()
        sweden = self.db_session.exec(
            select(func.count()).where(func.lower(col(Job.country)) == "sweden")
        ).one()
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        new7d = self.db_session.exec(
            select(func.count()).where(Job.created_at >= cutoff)
        ).one()
        positive_matches = self.db_session.exec(
            select(func.count()).where(col(Job.positive_keyword_match).is_(True))
        ).one()

        return JobSummary(
            counts_by_source=counts_by_source,
            counts_by_country=counts_by_country,
            counts_by_remote_status=counts_by_remote_status,
            to_review=to_review,
            eu_remote=eu_remote,
            sweden=sweden,
            new7d=new7d,
            positive_matches=positive_matches,
        )
