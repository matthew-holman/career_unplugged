from __future__ import annotations

from typing import Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import JobPost, Source


class PersonioScraper(AtsScraper):
    @property
    def source_name(self) -> Source:
        return Source.PERSONIO

    @classmethod
    def supports(cls, *, url: str, soup: BeautifulSoup) -> bool:
        html = str(soup).lower()
        if "personio.de" in html:
            return True

        tab_container = soup.select_one("div#tab-container")
        if tab_container and tab_container.select_one("a.job-box-link"):
            return True

        return False

    def find_job_cards(self, soup: BeautifulSoup) -> Iterable[object]:
        container = soup.select_one("div#tab-container") or soup

        cards = container.select("a.job-box-link[data-job-position-id]")
        if cards:
            return list(cards)

        cards = container.select("a.job-box-link")
        return list(cards)

    def parse_job_card(self, card: object) -> JobPost | None:
        if not isinstance(card, Tag):
            return None

        href = card.get("href")
        if not href:
            return None

        title = card.get("data-job-position-name")
        if not title:
            title_tag = card.select_one(".jb-title")
            title = title_tag.get_text(" ", strip=True) if title_tag else None
        if not title:
            return None

        location_raw = card.get("data-job-position-office")
        if not location_raw:
            location_tag = card.select_one(".jb-description strong")
            location_raw = (
                location_tag.get_text(" ", strip=True) if location_tag else None
            )

        job_url = urljoin(self.career_page.url, href)
        card_text = card.get_text(" ", strip=True)
        location, remote_status = self.extract_location_and_remote_status(
            card_text=card_text, location_hint=location_raw
        )

        return JobPost(
            title=title.strip(),
            company_name=self.company_name(),
            company_url=self.career_page.url,
            location=location,
            date_posted=None,
            job_url=job_url,
            job_type=None,
            description=None,
            remote_status=remote_status,
            source=self.source_name,
        )
