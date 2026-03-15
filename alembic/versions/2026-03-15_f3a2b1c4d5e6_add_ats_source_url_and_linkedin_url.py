"""Add ats_source_url and linkedin_url to job, drop source_url

Revision ID: f3a2b1c4d5e6
Revises: e71265f24e2d
Create Date: 2026-03-15 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f3a2b1c4d5e6"
down_revision = "e71265f24e2d"
branch_labels = None
depends_on = None


def upgrade():
    # 1) Add new nullable columns (no constraints yet — need data first)
    op.add_column("job", sa.Column("ats_source_url", sa.String(), nullable=True))
    op.add_column("job", sa.Column("linkedin_url", sa.String(), nullable=True))

    # 2) Populate from existing source_url based on source type
    op.execute(
        """
        UPDATE job
        SET linkedin_url = source_url
        WHERE source = 'linkedin'
        """
    )
    op.execute(
        """
        UPDATE job
        SET ats_source_url = source_url
        WHERE source != 'linkedin'
        """
    )

    # 3) Add unique constraints
    op.create_unique_constraint("job_ats_source_url_key", "job", ["ats_source_url"])
    op.create_unique_constraint("job_linkedin_url_key", "job", ["linkedin_url"])

    # 4) Drop old column and its constraint
    op.drop_constraint("job_source_url_key", "job", type_="unique")
    op.drop_column("job", "source_url")


def downgrade():
    # 1) Re-add source_url as nullable initially
    op.add_column("job", sa.Column("source_url", sa.String(), nullable=True))

    # 2) Restore data from whichever URL field is populated
    op.execute(
        """
        UPDATE job
        SET source_url = COALESCE(ats_source_url, linkedin_url)
        """
    )

    # 3) Restore unique constraint and NOT NULL
    op.alter_column("job", "source_url", nullable=False)
    op.create_unique_constraint("job_source_url_key", "job", ["source_url"])

    # 4) Drop new columns and their constraints
    op.drop_constraint("job_ats_source_url_key", "job", type_="unique")
    op.drop_constraint("job_linkedin_url_key", "job", type_="unique")
    op.drop_column("job", "ats_source_url")
    op.drop_column("job", "linkedin_url")
