from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import JobPost, Location, Source
from app.log import Log


@dataclass(frozen=True)
class GreenhouseEmbedJobCard:
    title: str
    location_raw: Optional[str]
    job_url: str
    department: Optional[str] = None
    remote_status_raw: Optional[str] = None


class GreenHouseEmbedScraper(AtsScraper):
    """
    Supports:
      A) Greenhouse official embed widget (div#grnhse_app + div.opening)
      B) Company-hosted pages with job links containing gh_jid=...
    """

    @property
    def source_name(self) -> Source:
        return Source.GREENHOUSE_EMBEDDED

    @classmethod
    def supports(cls, url: str) -> bool:
        # Exclude greenhouse board host; that’s GREENHOUSE_BOARD
        try:
            host = urlparse(url.strip()).netloc.lower()
        except ValueError:
            return False

        if host == "job-boards.greenhouse.io":
            return False

        response = cls._fetch_page(url)
        if not response:
            return False

        html = response.text.lower()

        # Variant A: official greenhouse embed widget
        if "grnhse_app" in html or "boards.greenhouse.io/embed" in html:
            return True

        # Variant B: site-hosted apply links using gh_jid
        if "gh_jid=" in html:
            return True

        return False

    def find_job_cards(self, soup: BeautifulSoup) -> list[Tag]:
        # Variant A: official embed widget
        grnhse_root = soup.select_one("#grnhse_app")
        if grnhse_root:
            openings = grnhse_root.select(".opening")
            if openings:
                return list(openings)

        # Variant B: gh_jid links anywhere on the page
        gh_links = soup.select('a[href*="gh_jid="]')
        if gh_links:
            # Return the <a> as the “card” to keep it simple.
            return list(gh_links)

        # Fallback: sometimes the embed is iframed or script-injected; you won't see it in HTML.
        Log.warning(f"Greenhouse embed: no recognizable job cards on {self.career_page.url}")
        return []

    def parse_job_card(self, job_card: Tag) -> Optional[JobPost]:
        parsed = self._parse_greenhouse_embed_card(job_card)
        if not parsed:
            return None

        # remote detection from location string (cheap and good enough)
        remote_status = None
        if parsed.location_raw:
            remote_status = self.parse_remote_status(parsed.location_raw)

        city, country = self.parse_location(parsed.location_raw)

        return JobPost(
            title=parsed.title,
            company_name=self.career_page.company_name,
            company_url=self.career_page.url,
            location=Location(city=city, country=country),
            date_posted=None,
            job_url=parsed.job_url,
            job_type=None,
            description=None,
            remote_status=remote_status,
            source=self.source_name,
        )

    @staticmethod
    def _parse_greenhouse_embed_card(card: Tag) -> Optional[GreenhouseEmbedJobCard]:
        """
        Supports:
          A) <div class="opening"><a href="...">Title</a><span class="location">X</span></div>
          B) <a href="...gh_jid=...">Title</a> with location nearby in the DOM
        """

        # Variant A: Greenhouse embed widget structure
        if "opening" in (card.get("class") or []):
            link = card.select_one("a[href]")
            if not link:
                return None

            job_url = (link.get("href") or "").strip()
            if not job_url:
                return None

            title = link.get_text(" ", strip=True)
            title = " ".join(title.split()).strip()
            if not title:
                return None

            location_tag = card.select_one(".location")
            location_raw = location_tag.get_text(" ", strip=True) if location_tag else None

            dept_tag = card.find_previous("h3")
            department = dept_tag.get_text(" ", strip=True) if dept_tag else None

            return GreenhouseEmbedJobCard(
                title=title,
                location_raw=location_raw,
                job_url=job_url,
                department=department,
            )

        # Variant B: card is the <a href*="gh_jid=">
        if card.name == "a":
            job_url = (card.get("href") or "").strip()
            if not job_url:
                return None

            title = card.get_text(" ", strip=True)
            title = " ".join(title.split()).strip()
            if not title:
                return None

            # Heuristic: location is often near the link (parent container text)
            # Try: look for the closest parent that looks like a list item / block and extract non-title text.
            container = card.find_parent(["li", "div", "p"]) or card.parent
            location_raw = None
            if container and isinstance(container, Tag):
                # candidate texts around the link
                # Prefer elements following the link in the same container.
                # e.g. <a>Title</a> <span>Berlin</span> or next <p>
                location_candidate = None
                next_span = card.find_next_sibling(["span", "p", "div"])
                if isinstance(next_span, Tag):
                    location_candidate = next_span.get_text(" ", strip=True)

                if location_candidate:
                    location_raw = " ".join(location_candidate.split()).strip()
                else:
                    # fallback: container text minus title (rough)
                    all_text = container.get_text("\n", strip=True)
                    all_text = all_text.replace(title, "").strip()
                    # pick first non-empty line
                    for line in [x.strip() for x in all_text.splitlines()]:
                        if line:
                            location_raw = line
                            break

            return GreenhouseEmbedJobCard(
                title=title,
                location_raw=location_raw,
                job_url=job_url,
            )

        return None
