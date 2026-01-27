from __future__ import annotations

from typing import Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import JobPost, Location, Source


class PersonioScraper(AtsScraper):
    @property
    def source_name(self) -> Source:
        return Source.PERSONIO

    @classmethod
    def supports(cls, soup: BeautifulSoup) -> bool:
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
        city, country = self.parse_location(location_raw)

        remote_status = (
            self.extract_remote_from_location(location_raw)
            or self.extract_remote_from_location(title)
            or self.parse_remote_status(location_raw)
            or self.parse_remote_status(title)
        )

        return JobPost(
            title=title.strip(),
            company_name=self.company_name(),
            company_url=self.career_page.url,
            location=Location(city=city, country=country),
            date_posted=None,
            job_url=job_url,
            job_type=None,
            description=None,
            remote_status=remote_status,
            source=self.source_name,
        )
