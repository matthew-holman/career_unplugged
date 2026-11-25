"""Reactivate working Jobylon career pages and deactivate non-boards

Most of these boards were deactivated with HTTP 403 before the Jobylon scraper
existed: Cloudflare blocked the bare "Mozilla/5.0" user agent the scrapers sent
then. With the browser user agent they load, and each was checked to be
claimed by JobylonScraper. Two others had a transient SSL error.

The *.jobylon.com hosts deactivated below are Jobylon's own infrastructure
(CDN, job pages, website) rather than company boards, and www.meca.se has no
Jobylon embed (the board is karriar.meca.se). They are also removed from the
seed file.

Revision ID: 6d2f8a1c3e5b
Revises: 4b8e2c6d1f3a
Create Date: 2026-11-25 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "6d2f8a1c3e5b"
down_revision = "4b8e2c6d1f3a"
branch_labels = None
depends_on = None

_REACTIVATE = (
    "https://arkwright.jobylon.com",
    "https://careers.dometic.com",
    "https://careers.einride.tech",
    "https://careers.lyko.com",
    "https://fora.jobylon.com",
    "https://jbmaskinteknik.jobylon.com",
    "https://jobb.hemglass.se",
    "https://karriar.coop.se",
    "https://karriar.fora.se",
    "https://lindab.jobylon.com",
    "https://mekosverige.jobylon.com",
    "https://muratafinland.com",
    "https://norrlandsbil.jobylon.com",
    "https://optinova.jobylon.com",
    "https://werkenbijhilverzorg.nl",
    "https://werkenbijprisma.nl",
    "https://werkenbijrhmdc.nl",
    "https://werkenbijvolth2.com",
    "https://www.werkenbijdetussenvoorziening.nl",
)

_DEACTIVATE = (
    "https://cdn.jobylon.com",
    "https://email.jobylon.com",
    "https://emp.jobylon.com",
    "https://media-eu.jobylon.com",
    "https://roadmap.jobylon.com",
    "https://static-eu.jobylon.com",
    "https://www.jobylon.com",
    "https://www.meca.se",
)


def _url_list(urls: tuple[str, ...]) -> str:
    return ", ".join(f"'{url}'" for url in urls)


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE career_page
        SET active = true, deactivated_at = NULL, last_status_code = NULL
        WHERE url IN ({_url_list(_REACTIVATE)})
          AND active = false
        """
    )
    op.execute(
        f"""
        UPDATE career_page
        SET active = false, deactivated_at = now()
        WHERE url IN ({_url_list(_DEACTIVATE)})
          AND active = true
        """
    )


def downgrade() -> None:
    # The previous states came from a blocked user agent and stale seeds;
    # restoring them would only switch working boards off again.
    pass
