"""Soft-delete duplicate Recruitee jobs saved with ?lang= URLs

The old Recruitee HTML scraper saved a job once per language link on the board
(e.g. /o/engineer?lang=de, ?lang=en), so one offer could appear several times.
The API scraper only produces the plain https://{slug}.recruitee.com/o/{offer}
URL, so the query-string variants would never be updated again.

For each offer:
- if no row uses the plain URL yet, the oldest variant is renamed to it, so the
  next sync updates that row instead of inserting a new one;
- applied/ignored state on the remaining variants is copied to the plain row;
- the remaining variants are soft-deleted.

Revision ID: 4b8e2c6d1f3a
Revises: 9e3b5d1f7a2c
Create Date: 2026-11-25 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "4b8e2c6d1f3a"
down_revision = "9e3b5d1f7a2c"
branch_labels = None
depends_on = None

_VARIANT = "ats_source_url LIKE 'https://%.recruitee.com/o/%?%'"
_PLAIN = "split_part(ats_source_url, '?', 1)"


def upgrade() -> None:
    # 1. Offers with no plain-URL row: promote the oldest live variant.
    #    The unique constraint covers soft-deleted rows too, so skip any plain
    #    URL that is already taken.
    op.execute(
        f"""
        UPDATE job j
        SET ats_source_url = keep.plain_url
        FROM (
            SELECT min(id) AS id, {_PLAIN} AS plain_url
            FROM job
            WHERE {_VARIANT} AND deleted_at IS NULL
            GROUP BY {_PLAIN}
        ) keep
        WHERE j.id = keep.id
          AND NOT EXISTS (
              SELECT 1 FROM job p WHERE p.ats_source_url = keep.plain_url
          )
        """
    )

    # 2. Carry applied/ignored state from the variants over to the plain row.
    op.execute(
        f"""
        INSERT INTO user_job (user_id, job_id, applied, ignored)
        SELECT u.user_id, p.id, bool_or(u.applied), bool_or(u.ignored)
        FROM job v
        JOIN user_job u ON u.job_id = v.id
        JOIN job p
          ON p.ats_source_url = split_part(v.ats_source_url, '?', 1)
         AND p.deleted_at IS NULL
        WHERE v.{_VARIANT} AND v.deleted_at IS NULL
        GROUP BY u.user_id, p.id
        ON CONFLICT (user_id, job_id) DO UPDATE
        SET applied = user_job.applied OR excluded.applied,
            ignored = user_job.ignored OR excluded.ignored
        """
    )

    # 3. Soft-delete the variants that now have a live plain row.
    op.execute(
        f"""
        UPDATE job v
        SET deleted_at = now()
        WHERE v.{_VARIANT}
          AND v.deleted_at IS NULL
          AND EXISTS (
              SELECT 1 FROM job p
              WHERE p.ats_source_url = split_part(v.ats_source_url, '?', 1)
                AND p.deleted_at IS NULL
          )
        """
    )


def downgrade() -> None:
    # The duplicates carried no extra information; nothing to restore.
    pass
