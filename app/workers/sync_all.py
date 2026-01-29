from __future__ import annotations

from typing import Any

from dotenv import load_dotenv

from app.log import Log
from app.workers.sync_ats import run_sync_ats
from app.workers.sync_linkedin import run_sync_linkedin


def run_sync_all() -> dict[str, Any]:
    load_dotenv()
    Log.setup(application_name="sync_all")

    ats_summary = run_sync_ats()
    linkedin_summary = run_sync_linkedin()

    return {
        "ats": ats_summary,
        "linkedin": linkedin_summary,
    }


def main() -> int:
    run_sync_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
