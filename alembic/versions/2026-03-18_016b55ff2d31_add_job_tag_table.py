"""add_job_tag_table

Revision ID: 016b55ff2d31
Revises: d4e5f6a7b8c9
Create Date: 2026-03-18 15:45:55.009318

"""

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision = "016b55ff2d31"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "job_tag",
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "category",
            sa.Enum("TECH_STACK", "ROLE_TYPE", name="tagcategory"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["job.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "name"),
    )
    op.create_index(op.f("ix_job_tag_job_id"), "job_tag", ["job_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_job_tag_job_id"), table_name="job_tag")
    op.drop_table("job_tag")
    op.execute("DROP TYPE IF EXISTS tagcategory")
