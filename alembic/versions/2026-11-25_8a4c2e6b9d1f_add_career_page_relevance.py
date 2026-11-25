"""Add relevance and relevance_locked to career_page

Relevance rates a career page by where its jobs are, so the ATS sync can scan
pages that never list a relevant job less often. Existing pages start as
UNKNOWN and are rated on their next scan.

Revision ID: 8a4c2e6b9d1f
Revises: 6d2f8a1c3e5b
Create Date: 2026-11-25 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "8a4c2e6b9d1f"
down_revision = "6d2f8a1c3e5b"
branch_labels = None
depends_on = None

_RELEVANCE = sa.Enum(
    "UNKNOWN",
    "TARGET",
    "REMOTE_OUTSIDE_EUROPE",
    "EUROPE_ONSITE",
    "OUTSIDE_EUROPE",
    name="careerpagerelevance",
)


def upgrade() -> None:
    _RELEVANCE.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "career_page",
        sa.Column("relevance", _RELEVANCE, nullable=False, server_default="UNKNOWN"),
    )
    op.add_column(
        "career_page",
        sa.Column(
            "relevance_locked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("career_page", "relevance_locked")
    op.drop_column("career_page", "relevance")
    _RELEVANCE.drop(op.get_bind(), checkfirst=True)
