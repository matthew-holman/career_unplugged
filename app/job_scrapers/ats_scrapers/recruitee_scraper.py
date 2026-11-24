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

RECRUITEE_HOST_SUFFIX = ".recruitee.com"


def recruitee_board_host(url: str) -> str | None:
    """Return the {slug}.recruitee.com host of a Recruitee URL, if it is one."""
    try:
        hostname = (urlparse(url).hostname or "").lower()
    except ValueError:
        return None
    if not hostname.endswith(RECRUITEE_HOST_SUFFIX):
        return None
    if hostname == RECRUITEE_HOST_SUFFIX.lstrip("."):
        return None
    return hostname


def recruitee_job_url(host: str, offer_slug: str) -> str:
    return f"https://{host}/o/{offer_slug}"


@dataclass(frozen=True)
class RecruiteeLocation:
    city: str | None
    country: str | None

    def as_hint(self) -> str | None:
        parts = [part for part in (self.city, self.country) if part]
        return ", ".join(parts) if parts else None


@dataclass(frozen=True)
class RecruiteeJobCard:
    title: str
    slug: str
    department: str | None
    employment_type: str | None
    published_at: str | None
    remote: bool
    hybrid: bool
    on_site: bool
    locations: tuple[RecruiteeLocation, ...]


class RecruiteeScraper(AtsScraper):
    """
    Scrapes {slug}.recruitee.com boards via the public offers API:
    GET https://{slug}.recruitee.com/api/offers/

    The API returns every published offer, including boards whose landing page
    is a custom layout that only links to sub-pages, or that paginate jobs.
    Job URLs use Recruitee's board format https://{slug}.recruitee.com/o/{offer}
    rather than the payload's careers_url, which may point at a custom domain.
    """

    @property
    def source_name(self) -> Source:
        return Source.RECRUITEE

    @classmethod
    def supports(cls, *, url: str, soup: BeautifulSoup) -> bool:
        return recruitee_board_host(url) is not None

    def find_job_cards(self, soup: BeautifulSoup) -> list[RecruiteeJobCard]:
        name = self.__class__.__name__
        host = recruitee_board_host(self.career_page.url)
        if not host:
            Log.warning(f"{name}: not a Recruitee board URL {self.career_page.url}")
            return []

        api_url = f"https://{host}/api/offers/"
        Log.info(f"Fetching {name} jobs from {api_url}")
        try:
            response = self._fetch_page(api_url, return_errors=True)
        except ConnectionError:
            Log.warning(f"{name}: connection error {api_url}")
            return []
        if response is None:
            return []
        if response.status_code == 429:
            Log.warning(f"{name}: rate limited on {api_url}")
            return []
        if response.status_code != 200:
            Log.warning(f"{name}: failed to fetch {api_url}: {response.status_code}")
            return []

        try:
            payload: object = response.json()
        except ValueError:
            Log.warning(f"{name}: invalid JSON from {api_url}")
            return []

        return self.parse_offers_payload(payload)

    @classmethod
    def parse_offers_payload(cls, payload: object) -> list[RecruiteeJobCard]:
        if not isinstance(payload, dict):
            return []
        offers = payload.get("offers")
        if not isinstance(offers, list):
            return []
        cards: list[RecruiteeJobCard] = []
        for offer in offers:
            card = cls._parse_offer(offer)
            if card:
                cards.append(card)
            else:
                Log.warning(f"{cls.__name__}: skipping offer without title/slug")
        return cards

    @classmethod
    def _parse_offer(cls, offer: object) -> RecruiteeJobCard | None:
        if not isinstance(offer, dict):
            return None
        title = _str_or_none(offer.get("title"))
        slug = _str_or_none(offer.get("slug"))
        if not title or not slug:
            return None

        locations: list[RecruiteeLocation] = []
        raw_locations = offer.get("locations")
        if isinstance(raw_locations, list):
            for raw in raw_locations:
                if not isinstance(raw, dict):
                    continue
                location = RecruiteeLocation(
                    city=_str_or_none(raw.get("city")),
                    country=_str_or_none(raw.get("country")),
                )
                if location.as_hint() and location not in locations:
                    locations.append(location)
        if not locations:
            fallback = RecruiteeLocation(
                city=_str_or_none(offer.get("city")),
                country=_str_or_none(offer.get("country")),
            )
            if fallback.as_hint():
                locations.append(fallback)

        return RecruiteeJobCard(
            title=title,
            slug=slug,
            department=_str_or_none(offer.get("department")),
            employment_type=_str_or_none(offer.get("employment_type_code")),
            published_at=_str_or_none(offer.get("published_at")),
            remote=offer.get("remote") is True,
            hybrid=offer.get("hybrid") is True,
            on_site=offer.get("on_site") is True,
            locations=tuple(locations),
        )

    def parse_job_card(self, card: object) -> JobPost | None:
        if not isinstance(card, RecruiteeJobCard):
            Log.warning(f"{self.__class__.__name__} got unexpected card type")
            return None

        host = recruitee_board_host(self.career_page.url)
        if not host:
            return None

        location_hint = self._pick_location_hint(card.locations)
        card_text = " ".join(
            part for part in (card.title, location_hint) if part is not None
        )
        location, remote_status = self.extract_location_and_remote_status(
            card_text=card_text, location_hint=location_hint
        )
        flag_status = _remote_status_from_flags(card)
        if flag_status is not None:
            remote_status = flag_status

        job_type = self.parse_job_type(card.employment_type)

        return JobPost(
            title=card.title,
            company_name=self.company_name(),
            company_url=self.career_page.url,
            location=location,
            date_posted=_parse_date(card.published_at),
            job_url=recruitee_job_url(host, card.slug),
            job_type=[job_type] if job_type else None,
            description=None,
            remote_status=remote_status,
            source=self.source_name,
        )

    @classmethod
    def _pick_location_hint(
        cls,
        locations: tuple[RecruiteeLocation, ...],
    ) -> str | None:
        """Prefer a European location when an offer lists several."""
        hints = [hint for hint in (loc.as_hint() for loc in locations) if hint]
        if len(hints) > 1:
            for hint in hints:
                # Country names are localised ("Deutschland"); normalise first.
                _, country = cls.parse_location(hint)
                if EuropeFilter.is_european(country):
                    return hint
        return hints[0] if hints else None


def _remote_status_from_flags(card: RecruiteeJobCard) -> RemoteStatus | None:
    """Recruitee's workplace flags; the most remote-friendly one wins."""
    if card.remote:
        return RemoteStatus.REMOTE
    if card.hybrid:
        return RemoteStatus.HYBRID
    if card.on_site:
        return RemoteStatus.ONSITE
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
