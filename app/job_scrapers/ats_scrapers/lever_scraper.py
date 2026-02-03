from dataclasses import dataclass
from typing import Iterable, Optional, cast
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import JobPost, Source
from app.log import Log


@dataclass(frozen=True)
class LeverJobCard:
    title: str
    location_raw: Optional[str]
    job_url: str


class LeverScraper(AtsScraper):

    @property
    def source_name(self) -> Source:
        return Source.LEVER

    @classmethod
    def supports(cls, *, url: str, soup: BeautifulSoup) -> bool:
        html = str(soup).lower()
        if "lever-jobs-embed" in html or "lever.co" in html:
            return True
        return False

    def find_job_cards(self, soup: BeautifulSoup) -> Iterable[object]:
        cards = soup.select("a.posting-title[href]")
        if cards:
            return list(cards)

        cards = soup.select("div.posting")
        if cards:
            return list(cards)

        if soup.select_one("script[src*='lever-jobs-embed']") or soup.select_one(
            ".lever-jobs-container"
        ):
            Log.warning(
                f"{self.__class__.__name__}: job data is loaded via JS on "
                f"{self.career_page.url}"
            )
        return []

    def parse_job_card(self, card: object) -> Optional[JobPost]:
        if not isinstance(card, Tag):
            return None
        card_tag = cast(Tag, card)

        parsed = self._parse_lever_job_card(card_tag)
        if not parsed:
            return None

        card_text = card_tag.get_text(" ", strip=True)
        location, remote_status = AtsScraper.extract_location_and_remote_status(
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

    def _parse_lever_job_card(self, card: Tag) -> Optional[LeverJobCard]:
        link = self._extract_job_link(card)
        if not link:
            return None

        job_url = (link.get("href") or "").strip()
        if not job_url:
            return None

        job_url = urljoin(self.career_page.url, job_url)

        title = self._extract_title(link)
        if not title:
            return None

        location_raw = self._extract_location(card, link)

        return LeverJobCard(
            title=title,
            location_raw=location_raw,
            job_url=job_url,
        )

    @staticmethod
    def _extract_job_link(card: Tag) -> Optional[Tag]:
        if card.name == "a" and card.get("href"):
            return card
        return card.select_one("a.posting-title[href]") or card.select_one("a[href]")

    @staticmethod
    def _extract_title(link: Tag) -> Optional[str]:
        title_tag = link.select_one("[data-qa='posting-name']")
        if not title_tag:
            title_tag = link.find(["h1", "h2", "h3", "h4", "h5"])

        if title_tag:
            title = title_tag.get_text(" ", strip=True)
        else:
            title = next((text for text in link.stripped_strings), "")

        title = " ".join(title.split()).strip()
        return title or None

    @staticmethod
    def _extract_location(card: Tag, link: Tag) -> Optional[str]:
        location_tag = link.select_one("[data-qa='posting-location']")
        if not location_tag:
            location_tag = link.select_one(".sort-by-location")
        if not location_tag:
            location_tag = card.select_one(".sort-by-location")
        if not location_tag:
            location_tag = card.select_one(".location")

        if not location_tag:
            return None

        location = location_tag.get_text(" ", strip=True)
        location = " ".join(location.split()).strip()
        return location or None
