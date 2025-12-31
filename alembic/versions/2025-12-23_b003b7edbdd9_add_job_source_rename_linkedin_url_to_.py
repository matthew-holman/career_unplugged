"""Add job source, rename linkedin_url to generic name

Revision ID: b003b7edbdd9
Revises: 3cf17d40f615
Create Date: 2025-12-23 09:33:42.024216

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b003b7edbdd9"
down_revision = "3cf17d40f615"
branch_labels = None
depends_on = None


def upgrade():

    # 1) Create enum type in Postgres BEFORE using it
    source_enum = sa.Enum(
        "LINKEDIN",
        "TEAMTAILOR",
        "GREENHOUSE_BOARD",
        "GREENHOUSE_EMBED",
        "ASHBY",
        "LEVER",
        "RECRUITEE",
        "RIPPLING",
        name="source",
    )
    bind = op.get_bind()
    source_enum.create(bind, checkfirst=True)

    # 2) Add the new 'source' column with a server default so existing rows pass NOT NULL
    op.add_column(
        "job",
        sa.Column(
            "source",
            source_enum,
            nullable=False,
            server_default="LINKEDIN",
        ),
    )

    # 3) Rename linkedin_url -> source_url (keeps existing data)
    op.alter_column("job", "linkedin_url", new_column_name="source_url")

    # 4) Swap the unique constraint to the new column name
    op.drop_constraint("job_linkedin_url_key", "job", type_="unique")
    op.create_unique_constraint("job_source_url_key", "job", ["source_url"])

    # 5) Remove the server default (optional, but cleaner long-term)
    op.alter_column("job", "source", server_default=None)


def downgrade():
    # reverse unique constraint swap
    op.drop_constraint("job_source_url_key", "job", type_="unique")
    op.create_unique_constraint("job_linkedin_url_key", "job", ["linkedin_url"])

    # rename back
    op.alter_column("job", "source_url", new_column_name="linkedin_url")

    # drop the enum column
    op.drop_column("job", "source")

    # optionally also drop the enum type in Postgres
    # (Only do this if you're sure nothing else uses it)
    op.execute("DROP TYPE IF EXISTS source")
