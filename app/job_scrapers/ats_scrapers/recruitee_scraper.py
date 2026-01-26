from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import JobPost, Location, Source
from app.log import Log


@dataclass(frozen=True)
class _LocationMatch:
    location_raw: str | None
    remote_status_raw: str | None


class RecruiteeScraper(AtsScraper):
    @property
    def source_name(self) -> Source:
        return Source.RECRUITEE

    @classmethod
    def supports(cls, url: str) -> bool:
        response = cls._fetch_page(url)
        if response:
            html = response.text.lower()
        else:
            return False

        if "recruiteecdn" in html and 'data-testid="offer-list-grid"' in html:
            Log.debug(f"Detected {cls.__name__} page with jobs list on {url}")
            return True

        return False

    def find_job_cards(self, soup: BeautifulSoup) -> list[Tag]:
        containers = soup.select('[data-testid="offer-list-grid"]')
        if not containers:
            containers = [soup]

        href_map: dict[str, tuple[Tag, int]] = {}

        for container in containers:
            for anchor in container.select('a[href^="/o/"]'):
                href = anchor.get("href")
                if not href:
                    continue
                text = anchor.get_text(" ", strip=True)
                text_len = len(text)
                existing = href_map.get(href)
                if not existing or text_len > existing[1]:
                    href_map[href] = (anchor, text_len)

        return [item[0] for item in href_map.values()]

    def parse_job_card(self, card: object) -> JobPost | None:
        if not isinstance(card, Tag):
            Log.warning(f"{self.__class__.__name__} got non-Tag card")
            return None

        href = card.get("href")
        if not href:
            return None

        title = card.get_text(strip=True)
        if not title:
            return None

        job_url = urljoin(self.career_page.url, href)

        location_match = self._extract_location_match(card)
        city, country = self.parse_location(location_match.location_raw)

        remote_status = self.extract_remote_from_location(
            location_match.remote_status_raw
        ) or self.parse_remote_status(location_match.remote_status_raw)

        return JobPost(
            title=title,
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

    def _extract_location_match(self, anchor: Tag) -> _LocationMatch:
        for parent in self._iter_parent_cards(anchor):
            location_raw = self._extract_location_from_container(parent)
            if location_raw:
                return _LocationMatch(
                    location_raw=location_raw,
                    remote_status_raw=location_raw,
                )

        for parent in self._iter_parent_cards(anchor):
            fallback = self._extract_location_fallback(parent)
            if fallback:
                return _LocationMatch(
                    location_raw=fallback,
                    remote_status_raw=fallback,
                )

        return _LocationMatch(location_raw=None, remote_status_raw=None)

    @staticmethod
    def _iter_parent_cards(anchor: Tag) -> list[Tag]:
        parents: list[Tag] = []
        current: Tag | None = anchor
        for _ in range(6):
            if current is None:
                break
            parents.append(current)
            current = current.parent if isinstance(current.parent, Tag) else None
        return parents

    @staticmethod
    def _extract_location_from_container(container: Tag) -> str | None:
        location_items = container.select('[data-testid="styled-location-list-item"]')
        if not location_items:
            return None

        for item in location_items:
            parts = RecruiteeScraper._extract_location_parts(item)
            if not parts:
                continue
            if len(parts) >= 2:
                city = parts[0]
                country = parts[-1]
                if city and country and city != country:
                    return f"{city}, {country}"
                return city or country
            return parts[0]

        return None

    @staticmethod
    def _extract_location_parts(item: Tag) -> list[str]:
        span_texts: list[str] = []
        custom_spans = item.find_all(
            "span",
            class_=lambda c: isinstance(c, str)
            and "custom-css-style-job-location-" in c,
        )
        spans = custom_spans or item.find_all("span")

        for span in spans:
            text = span.get_text(" ", strip=True)
            if text:
                span_texts.append(text)

        if not span_texts:
            text = item.get_text(" ", strip=True)
            if text:
                return [text]

        return span_texts

    @staticmethod
    def _extract_location_fallback(container: Tag) -> str | None:
        candidates: list[str] = []
        for tag in container.find_all(True):
            attrs = " ".join(
                str(value) for value in tag.attrs.values() if value is not None
            ).lower()
            if "location" in attrs:
                text = tag.get_text(" ", strip=True)
                if text:
                    candidates.append(text)

        if candidates:
            return max(candidates, key=len)

        text = container.get_text(" ", strip=True)
        return text if text else None
