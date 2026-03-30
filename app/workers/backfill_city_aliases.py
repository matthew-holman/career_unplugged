from sqlalchemy import func
from sqlmodel import col, select

from app.db.db import get_db
from app.log import Log
from app.models.job import Job
from app.utils.locations.country_resolver import CountryResolver


def main() -> int:
    Log.setup(application_name="backfill_city_aliases")

    alias_keys = list(CountryResolver.CITY_ALIASES.keys())

    with next(get_db()) as db_session:
        jobs = db_session.exec(
            select(Job).where(
                col(Job.deleted_at).is_(None),
                func.lower(col(Job.city)).in_(alias_keys),
            )
        ).all()

        updated = 0
        for job in jobs:
            if job.city is None:
                continue
            resolved = CountryResolver.resolve_alias(job.city)
            if resolved != job.city:
                Log.info(f"Updating city on job {job.id}: {job.city!r} -> {resolved!r}")
                job.city = resolved
                updated += 1

        db_session.commit()
        Log.info(f"Done: updated={updated}, scanned={len(jobs)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
