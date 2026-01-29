"""add job career page id

Revision ID: 1f2e3d4c5b6a
Revises: 9b1a2f6d7e4c
Create Date: 2026-02-02 11:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "1f2e3d4c5b6a"
down_revision = "9b1a2f6d7e4c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "job",
        sa.Column("career_page_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_job_career_page_id"),
        "job",
        ["career_page_id"],
        unique=False,
    )
    op.create_foreign_key(
        "job_career_page_id_fkey",
        "job",
        "career_page",
        ["career_page_id"],
        ["id"],
    )

    op.execute(
        """
        UPDATE job AS j
        SET career_page_id = cp.id
        FROM career_page AS cp
        WHERE j.career_page_id IS NULL
          AND j.company IS NOT NULL
          AND cp.company_name IS NOT NULL
          AND lower(j.company) = lower(cp.company_name)
        """
    )


def downgrade():
    op.drop_constraint("job_career_page_id_fkey", "job", type_="foreignkey")
    op.drop_index(op.f("ix_job_career_page_id"), table_name="job")
    op.drop_column("job", "career_page_id")
