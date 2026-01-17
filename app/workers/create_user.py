import argparse

from app.db.db import get_db
from app.handlers.user import UserHandler
from app.log import Log
from app.models.user import User

USER_UPSERT_EXCLUDE = {"id", "created_at", "updated_at", "deleted_at"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update a user")
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    return parser.parse_args()


def main() -> int:
    Log.setup(application_name="create_user")
    args = parse_args()

    with next(get_db()) as db_session:
        create_user = User(name=args.name, email=args.email)
        user_handler = UserHandler(db_session)
        user_handler.save(create_user)
        db_session.commit()
        persisted_user = user_handler.get(create_user.email)
        if not persisted_user:
            print("Error while creating user.")
            return 1
        print(f"user id: {persisted_user.id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
