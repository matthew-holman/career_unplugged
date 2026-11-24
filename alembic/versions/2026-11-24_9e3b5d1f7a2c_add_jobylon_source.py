"""Add jobylon job source

Revision ID: 9e3b5d1f7a2c
Revises: 7c1d9e4a2b6f
Create Date: 2026-11-24 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "9e3b5d1f7a2c"
down_revision = "7c1d9e4a2b6f"
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
    "WORKABLE",
]
_SOURCES_AFTER = sorted([*_SOURCES_BEFORE, "JOBYLON"])


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
