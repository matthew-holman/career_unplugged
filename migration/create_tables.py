from sqlmodel import SQLModel

# Import models so they are registered on SQLModel.metadata
import app.models  # noqa: F401

from app.db.db import engine

if __name__ == "__main__":
    SQLModel.metadata.create_all(engine)
