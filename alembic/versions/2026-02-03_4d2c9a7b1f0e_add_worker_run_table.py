"""add worker run table

Revision ID: 4d2c9a7b1f0e
Revises: 1f2e3d4c5b6a
Create Date: 2026-02-03 10:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "4d2c9a7b1f0e"
down_revision = "1f2e3d4c5b6a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "worker_run",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("worker_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("errors", sa.JSON(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index(op.f("ix_worker_run_run_id"), "worker_run", ["run_id"], unique=True)
    op.create_index(
        op.f("ix_worker_run_status"), "worker_run", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_worker_run_worker_name"),
        "worker_run",
        ["worker_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_worker_run_created_at"), "worker_run", ["created_at"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_worker_run_created_at"), table_name="worker_run")
    op.drop_index(op.f("ix_worker_run_worker_name"), table_name="worker_run")
    op.drop_index(op.f("ix_worker_run_status"), table_name="worker_run")
    op.drop_index(op.f("ix_worker_run_run_id"), table_name="worker_run")
    op.drop_table("worker_run")
