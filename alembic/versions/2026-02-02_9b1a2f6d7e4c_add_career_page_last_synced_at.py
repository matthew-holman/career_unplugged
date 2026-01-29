"""add career page last synced at

Revision ID: 9b1a2f6d7e4c
Revises: 2e9b8c9c4d6b
Create Date: 2026-02-02 10:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "9b1a2f6d7e4c"
down_revision = "2e9b8c9c4d6b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "career_page",
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column("career_page", "last_synced_at")
