"""Add remote_score to job

Revision ID: f1a2b3c4d5e6
Revises: 95ad9dc508cb
Create Date: 2026-03-21 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f1a2b3c4d5e6"
down_revision = "95ad9dc508cb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job",
        sa.Column(
            "remote_score",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("job", "remote_score")
