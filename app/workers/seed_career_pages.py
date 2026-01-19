from app.db.db import get_db
from app.log import Log
from app.seeds.career_pages import CareerPageSeeder


def main() -> int:
    Log.setup(application_name="seed_career_pages")
    with next(get_db()) as db_session:
        CareerPageSeeder(db_session).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
