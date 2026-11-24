"""Add workable job source

Revision ID: 7c1d9e4a2b6f
Revises: 35ed2a4e2535
Create Date: 2026-11-24 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "7c1d9e4a2b6f"
down_revision = "35ed2a4e2535"
branch_labels = None
depends_on = None

_SOURCES_BEFORE = [
    "ASHBY",
    "BAMBOO",
    "GREENHOUSE_BOARD",
    "GREENHOUSE_EMBEDDED",
    "HIBOB",
    "LEVER",
    "LINKEDIN",
    "PERSONIO",
    "RECRUITEE",
    "RIPPLING",
    "TEAMTAILOR",
]
_SOURCES_AFTER = sorted([*_SOURCES_BEFORE, "WORKABLE"])


def upgrade():
    op.sync_enum_values(
        "public",
        "source",
        _SOURCES_BEFORE,
        _SOURCES_AFTER,
        [("job", "source")],
        False,
    )


def downgrade():
    op.sync_enum_values(
        "public",
        "source",
        _SOURCES_AFTER,
        _SOURCES_BEFORE,
        [("job", "source")],
        True,
    )
