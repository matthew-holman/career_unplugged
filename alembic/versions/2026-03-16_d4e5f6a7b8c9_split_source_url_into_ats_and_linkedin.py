"""Split source_url into ats_source_url and linkedin_source_url

Revision ID: d4e5f6a7b8c9
Revises: e71265f24e2d
Create Date: 2026-03-16 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "e71265f24e2d"
branch_labels = None
depends_on = None


def upgrade():
    # 1) Rename source_url -> ats_source_url (keeps existing ATS data intact)
    op.alter_column("job", "source_url", new_column_name="ats_source_url")

    # 2) Swap the unique constraint to the new column name
    op.drop_constraint("job_source_url_key", "job", type_="unique")
    op.create_unique_constraint("job_ats_source_url_key", "job", ["ats_source_url"])

    # 3) Make ats_source_url nullable (LinkedIn-only jobs won't have an ATS URL)
    op.alter_column("job", "ats_source_url", nullable=True)

    # 4) Add linkedin_source_url column (nullable, unique)
    op.add_column(
        "job",
        sa.Column("linkedin_source_url", sa.String(), nullable=True),
    )
    op.create_unique_constraint(
        "job_linkedin_source_url_key", "job", ["linkedin_source_url"]
    )


def downgrade():
    # Drop linkedin_source_url
    op.drop_constraint("job_linkedin_source_url_key", "job", type_="unique")
    op.drop_column("job", "linkedin_source_url")

    # Restore ats_source_url -> source_url as NOT NULL
    op.drop_constraint("job_ats_source_url_key", "job", type_="unique")
    op.alter_column("job", "ats_source_url", new_column_name="source_url")
    op.alter_column("job", "source_url", nullable=False)
    op.create_unique_constraint("job_source_url_key", "job", ["source_url"])
