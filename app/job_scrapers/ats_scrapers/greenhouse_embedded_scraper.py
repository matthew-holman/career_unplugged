from dataclasses import dataclass
from typing import Iterable, Optional

from bs4 import BeautifulSoup, Tag

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import JobPost, Source
from app.log import Log


@dataclass(frozen=True)
class GreenhouseEmbedJobCard:
    title: str
    location_raw: Optional[str]
    job_url: str
    department: Optional[str] = None


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
    def supports(cls, soup: BeautifulSoup) -> bool:
        html = str(soup).lower()
        if "greenhouse-job-board" in html or "greenhouse-board" in html:
            return True

        if soup.select_one("div.js-greenhouse-board"):
            return True

        if soup.select_one("li.cx-gh-open-position"):
            return True

        if soup.select_one('a[href*="gh_jid="]'):
            return True

        if soup.select_one('a[href*="job-boards.greenhouse.io"]'):
            return False

        if "greenhouse" in html:
            Log.warning(
                "This might be a Greenhouse page even though it's not been detected "
                "by this scraper."
            )
        return False

    def find_job_cards(self, soup: BeautifulSoup) -> Iterable[object]:
        # Variant A: official embed widget
        greenhouse_root = soup.select_one("div.js-greenhouse-board")
        if greenhouse_root:
            # eg https://api.greenhouse.io/v1/boards/addepar1/jobs the company path is not
            # the guaranteed to be the same as the main url
            Log.warning(
                f"Official Greenhouse embedded, requires API call with "
                f"correct path, not implemented yet for page {self.career_page.url}"
            )
            return []

        # Variant B: open position list items
        gh_links = soup.select("li.cx-gh-open-position")
        if gh_links:
            # Return the <a> as the “card” to keep it simple.
            return list(gh_links)

        # Fallback: sometimes the embed is iframed or script-injected; you won't see it in HTML.
        Log.warning(
            f"Greenhouse embed: no recognizable job cards on {self.career_page.url}"
        )
        return []

    def parse_job_card(self, job_card: Tag) -> Optional[JobPost]:
        parsed = self._parse_greenhouse_embed_card(job_card)
        if not parsed:
            return None

        card_text = job_card.get_text(" ", strip=True)
        location, remote_status = self.extract_location_and_remote_status(
            card_text=card_text, location_hint=parsed.location_raw
        )

        return JobPost(
            title=parsed.title,
            company_name=self.career_page.company_name,
            company_url=self.career_page.url,
            location=location,
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
            location_raw = (
                location_tag.get_text(" ", strip=True) if location_tag else None
            )

            dept_tag = card.find_previous("h3")
            department = dept_tag.get_text(" ", strip=True) if dept_tag else None

            return GreenhouseEmbedJobCard(
                title=title,
                location_raw=location_raw,
                job_url=job_url,
                department=department,
            )

        return GreenHouseEmbedScraper._parse_wordpress_open_position(card)

    @staticmethod
    def _parse_wordpress_open_position(card: Tag) -> Optional[GreenhouseEmbedJobCard]:
        """
        Variant B (WordPress plugin):
        <li class="cx-gh-open-position">
          <a href="...gh_jid=...">Title</a>
          <div class="cx-gh-location"><span class="location">Brazil</span></div>
          # sometimes also: <div class="tooltip-inner"><p>...</p></div>
        </li>
        """
        if card.name != "li" or "cx-gh-open-position" not in (card.get("class") or []):
            return None

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

        # Primary location text
        location_container = card.select_one(".cx-gh-location")
        location_raw: Optional[str] = None

        if location_container:
            # Prefer explicit multi-location content if present
            tooltip_paragraph = location_container.select_one(".tooltip-inner p")
            if tooltip_paragraph:
                location_raw = tooltip_paragraph.get_text(" ", strip=True)
            else:
                # Fallback: single location
                location_span = location_container.select_one(".location")
                if location_span:
                    location_raw = location_span.get_text(" ", strip=True)

        if location_raw:
            location_raw = " ".join(location_raw.split()).strip()

        return GreenhouseEmbedJobCard(
            title=title,
            location_raw=location_raw,
            job_url=job_url,
        )
