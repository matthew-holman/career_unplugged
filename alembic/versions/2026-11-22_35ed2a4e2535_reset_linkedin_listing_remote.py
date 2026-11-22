"""Reset LinkedIn listing_remote to UNKNOWN

LinkedIn jobs were stamped with the workplace filter of the search that returned
them, but LinkedIn's guest search mostly ignores that filter. Because remote
searches ran last, most LinkedIn jobs ended up stored as REMOTE regardless of
their real workplace type. Reset them to UNKNOWN.

Existing remote_score / true_remote values are left as they are; only jobs
analysed from now on are scored with the corrected status. Old jobs are not
re-queued for analysis: most of their LinkedIn postings have been removed, and
re-fetching them in bulk gets rate-limited.

Rows whose source is no longer LINKEDIN were updated by an ATS scrape and keep
their ATS-derived status.

Revision ID: 35ed2a4e2535
Revises: f1a2b3c4d5e6
Create Date: 2026-11-22 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "35ed2a4e2535"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE job
        SET listing_remote = 'UNKNOWN'
        WHERE source = 'LINKEDIN'
          AND deleted_at IS NULL
        """
    )


def downgrade() -> None:
    # The previous values came from an ignored search filter and carried no
    # information, so there is nothing meaningful to restore.
    pass
