"""Add scraper_status and scraper_checked_at to career_page

Records whether any ATS scraper matched a page, so pages no scraper can read
(custom-domain career sites found through LinkedIn apply links, say) are
fetched once and then only re-checked occasionally. Pages that have synced
before are marked SUPPORTED; the rest start UNCHECKED.

Revision ID: 3c7e9a2f5b8d
Revises: 8a4c2e6b9d1f
Create Date: 2026-11-26 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "3c7e9a2f5b8d"
down_revision = "8a4c2e6b9d1f"
branch_labels = None
depends_on = None

_SCRAPER_STATUS = sa.Enum(
    "UNCHECKED",
    "SUPPORTED",
    "UNSUPPORTED",
    name="careerpagescraperstatus",
)


def upgrade() -> None:
    _SCRAPER_STATUS.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "career_page",
        sa.Column(
            "scraper_status",
            _SCRAPER_STATUS,
            nullable=False,
            server_default="UNCHECKED",
        ),
    )
    op.add_column(
        "career_page",
        sa.Column("scraper_checked_at", sa.DateTime(), nullable=True),
    )
    op.execute(
        "UPDATE career_page "
        "SET scraper_status = 'SUPPORTED', scraper_checked_at = last_synced_at "
        "WHERE last_synced_at IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("career_page", "scraper_checked_at")
    op.drop_column("career_page", "scraper_status")
    _SCRAPER_STATUS.drop(op.get_bind(), checkfirst=True)
