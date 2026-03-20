"""remove_keyword_match_columns

Revision ID: 95ad9dc508cb
Revises: 016b55ff2d31
Create Date: 2026-03-20 09:56:27.963809

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "95ad9dc508cb"
down_revision = "016b55ff2d31"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("job", "negative_keyword_match")
    op.drop_column("job", "positive_keyword_match")


def downgrade():
    op.add_column(
        "job",
        sa.Column(
            "positive_keyword_match", sa.BOOLEAN(), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "job",
        sa.Column(
            "negative_keyword_match", sa.BOOLEAN(), autoincrement=False, nullable=True
        ),
    )
