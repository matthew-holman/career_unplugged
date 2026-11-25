"""Soft-delete career pages that are an ATS vendor's own host.

Discovery used to seed hosts such as ``status.teamtailor.com`` or
``www.recruitee.com`` as company boards. This marks every active page that
``is_vendor_host`` recognises as inactive.

Usage
-----
    poetry run python -m app.workers.deactivate_vendor_career_pages [--dry-run]
"""

import argparse

from app.db.db import get_db
from app.handlers.career_page import CareerPageHandler
from app.log import Log
from app.seeds.discovery_sources import is_vendor_host


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dry-run", action="store_true", help="Only log the pages to deactivate"
    )
    args = parser.parse_args(argv)
    Log.setup(application_name="deactivate_vendor_career_pages")

    with next(get_db()) as db_session:
        handler = CareerPageHandler(db_session)
        vendor_pages = [
            page for page in handler.get_all_active() if is_vendor_host(page.url)
        ]
        for page in vendor_pages:
            Log.info(f"Deactivating vendor host career page {page.id}: {page.url}")
            if not args.dry_run:
                handler.deactivate(page)

        if args.dry_run:
            Log.info(f"Dry run: would deactivate {len(vendor_pages)} pages")
            return 0
        db_session.commit()
        Log.info(f"Done: deactivated={len(vendor_pages)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
