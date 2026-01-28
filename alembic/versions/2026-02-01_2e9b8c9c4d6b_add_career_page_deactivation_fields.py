"""add career page deactivation fields

Revision ID: 2e9b8c9c4d6b
Revises: 378e9db4feb3
Create Date: 2026-02-01 10:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "2e9b8c9c4d6b"
down_revision = "378e9db4feb3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "career_page",
        sa.Column("deactivated_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "career_page",
        sa.Column("last_status_code", sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_column("career_page", "last_status_code")
    op.drop_column("career_page", "deactivated_at")
