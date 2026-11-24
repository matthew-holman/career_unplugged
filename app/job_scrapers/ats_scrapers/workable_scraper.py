from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from requests.exceptions import ConnectionError

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import JobPost, RemoteStatus, Source
from app.log import Log
from app.utils.locations.europe_filter import EuropeFilter

WORKABLE_HOST = "apply.workable.com"
# First path segments on apply.workable.com that are not company slugs.
# e.g. https://apply.workable.com/j/{shortcode} is a slug-less job shortlink.
WORKABLE_RESERVED_SEGMENTS = frozenset({"j", "api"})


def workable_account_slug(url: str) -> str | None:
    """Return the account slug from an apply.workable.com URL, if present."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if (parsed.hostname or "").lower() != WORKABLE_HOST:
        return None
    parts = [segment for segment in parsed.path.split("/") if segment]
    if not parts or parts[0].lower() in WORKABLE_RESERVED_SEGMENTS:
        return None
    return parts[0]


def workable_job_url(slug: str, shortcode: str) -> str:
    return f"https://{WORKABLE_HOST}/{slug}/j/{shortcode}/"


@dataclass(frozen=True)
class WorkableLocation:
    city: str | None
    region: str | None
    country: str | None

    def as_hint(self) -> str | None:
        parts = [part for part in (self.city, self.country) if part]
        if not parts and self.region:
            parts = [self.region]
        return ", ".join(parts) if parts else None


@dataclass(frozen=True)
class WorkableJobCard:
    title: str
    shortcode: str
    department: str | None
    employment_type: str | None
    telecommuting: bool
    published_on: str | None
    locations: tuple[WorkableLocation, ...]


class WorkableScraper(AtsScraper):
    """
    Scrapes apply.workable.com boards via the public widget API:
    GET https://apply.workable.com/api/v1/widget/accounts/{slug}

    The widget returns one row per (job, location), so rows are merged by
    shortcode. Job URLs use Workable's canonical board format
    https://apply.workable.com/{slug}/j/{shortcode}/ which also matches the
    apply links LinkedIn points to.
    """

    @property
    def source_name(self) -> Source:
        return Source.WORKABLE

    @classmethod
    def supports(cls, *, url: str, soup: BeautifulSoup) -> bool:
        return workable_account_slug(url) is not None

    def _widget_url(self) -> str | None:
        slug = workable_account_slug(self.career_page.url)
        if not slug:
            return None
        return f"https://{WORKABLE_HOST}/api/v1/widget/accounts/{slug}"

    def find_job_cards(self, soup: BeautifulSoup) -> list[WorkableJobCard]:
        widget_url = self._widget_url()
        if not widget_url:
            Log.warning(
                f"{self.__class__.__name__}: no account slug in "
                f"{self.career_page.url}"
            )
            return []

        Log.info(f"Fetching {self.__class__.__name__} jobs from {widget_url}")
        try:
            response = self._fetch_page(widget_url, return_errors=True)
        except ConnectionError:
            Log.warning(f"{self.__class__.__name__}: connection error {widget_url}")
            return []
        if response is None:
            return []
        if response.status_code == 429:
            Log.warning(f"{self.__class__.__name__}: rate limited on {widget_url}")
            return []
        if response.status_code == 404:
            Log.warning(
                f"{self.__class__.__name__}: account not found at {widget_url}; "
                "the board may have been removed"
            )
            return []
        if response.status_code != 200:
            Log.warning(
                f"{self.__class__.__name__}: failed to fetch {widget_url}: "
                f"{response.status_code}"
            )
            return []

        try:
            payload: object = response.json()
        except ValueError:
            Log.warning(f"{self.__class__.__name__}: invalid JSON from {widget_url}")
            return []

        return self.parse_widget_payload(payload)

    @classmethod
    def parse_widget_payload(cls, payload: object) -> list[WorkableJobCard]:
        if not isinstance(payload, dict):
            return []
        rows = payload.get("jobs")
        if not isinstance(rows, list):
            return []

        merged: dict[str, WorkableJobCard] = {}
        for row in rows:
            card = cls._parse_row(row)
            if not card:
                continue
            existing = merged.get(card.shortcode)
            if existing is None:
                merged[card.shortcode] = card
                continue
            extra = tuple(
                loc for loc in card.locations if loc not in existing.locations
            )
            merged[card.shortcode] = WorkableJobCard(
                title=existing.title,
                shortcode=existing.shortcode,
                department=existing.department,
                employment_type=existing.employment_type,
                telecommuting=existing.telecommuting or card.telecommuting,
                published_on=existing.published_on,
                locations=existing.locations + extra,
            )
        return list(merged.values())

    @classmethod
    def _parse_row(cls, row: object) -> WorkableJobCard | None:
        if not isinstance(row, dict):
            return None
        title = _str_or_none(row.get("title"))
        shortcode = _str_or_none(row.get("shortcode"))
        if not title or not shortcode:
            return None

        locations: list[WorkableLocation] = []
        raw_locations = row.get("locations")
        if isinstance(raw_locations, list):
            for raw in raw_locations:
                if not isinstance(raw, dict) or raw.get("hidden") is True:
                    continue
                locations.append(
                    WorkableLocation(
                        city=_str_or_none(raw.get("city")),
                        region=_str_or_none(raw.get("region")),
                        country=_str_or_none(raw.get("country")),
                    )
                )
        if not locations:
            fallback = WorkableLocation(
                city=_str_or_none(row.get("city")),
                region=_str_or_none(row.get("state")),
                country=_str_or_none(row.get("country")),
            )
            if fallback.as_hint():
                locations.append(fallback)

        return WorkableJobCard(
            title=title,
            shortcode=shortcode,
            department=_str_or_none(row.get("department")),
            employment_type=_str_or_none(row.get("employment_type")),
            telecommuting=row.get("telecommuting") is True,
            published_on=_str_or_none(row.get("published_on")),
            locations=tuple(locations),
        )

    def parse_job_card(self, card: object) -> JobPost | None:
        if not isinstance(card, WorkableJobCard):
            return None

        slug = workable_account_slug(self.career_page.url)
        if not slug:
            return None

        location_hint = self._pick_location_hint(card.locations)
        card_text = " ".join(
            part
            for part in (card.title, card.department, location_hint)
            if part is not None
        )
        location, remote_status = self.extract_location_and_remote_status(
            card_text=card_text, location_hint=location_hint
        )
        if card.telecommuting:
            remote_status = RemoteStatus.REMOTE

        job_type = self.parse_job_type(card.employment_type)

        return JobPost(
            title=card.title,
            company_name=self.career_page.company_name,
            company_url=self.career_page.url,
            location=location,
            date_posted=_parse_date(card.published_on),
            job_url=workable_job_url(slug, card.shortcode),
            job_type=[job_type] if job_type else None,
            description=None,
            remote_status=remote_status,
            source=self.source_name,
        )

    @staticmethod
    def _pick_location_hint(
        locations: tuple[WorkableLocation, ...],
    ) -> str | None:
        """Prefer a European location when a job lists several."""
        for loc in locations:
            if EuropeFilter.is_european(loc.country):
                return loc.as_hint()
        for loc in locations:
            hint = loc.as_hint()
            if hint:
                return hint
        return None


def _str_or_none(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None
