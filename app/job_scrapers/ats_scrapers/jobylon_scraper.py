from __future__ import annotations

import re

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from bs4 import BeautifulSoup, Tag
from requests.exceptions import ConnectionError

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import JobPost, Source
from app.log import Log

JOBYLON_CDN_HOST = "cdn.jobylon.com"
JOBYLON_JOBS_HOST = "emp.jobylon.com"
# Server-rendered list embed. Unlike v2 (Angular + JS object literal) it renders
# every job as plain HTML and honours the same filter params as the embedder.
JOBYLON_LIST_VERSION = "v5"

_EMBED_TYPES = {"company": "companies", "group": "company-groups"}
_EMBED_PATH_RE = re.compile(r"^/jobs/(companies|company-groups)/(\d+)/embed/")
_JOB_PATH_RE = re.compile(r"^/jobs/\d+[-/]")

_CONFIG_ID_RE = re.compile(
    r"\bjbl_(company|group)_id\s*=\s*['\"]?\s*(\d+)\s*['\"]?\s*;"
)
_FILTERS_RE = re.compile(r"\bjbl_filters\s*=\s*\{(?P<body>[^{}]*)\}\s*;")
_FILTER_ENTRY_RE = re.compile(
    r"^\s*(?P<key>[A-Za-z_]\w*)\s*:\s*(?:\[(?P<list>[^\[\]]*)\]|(?P<scalar>[^,\[\]]+))\s*$"
)
_FILTER_VALUE_RE = re.compile(r"^\s*(?:'([^']*)'|\"([^\"]*)\"|(-?\d+))\s*$")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
_LINE_COMMENT_RE = re.compile(r"^\s*//.*$", re.M)
# "Kista +1 more" / "Kista +1 till" / "+2 mere" — localised extra-locations suffix.
_EXTRA_LOCATIONS_RE = re.compile(r"\s*\+\d+\b.*$")


class JobylonFilterError(ValueError):
    """Raised when an inline jbl_filters block cannot be parsed with certainty."""


@dataclass(frozen=True)
class JobylonEmbed:
    embed_type: str  # "companies" | "company-groups"
    embed_id: str
    params: tuple[tuple[str, str], ...] = ()

    def list_url(self) -> str:
        base = (
            f"https://{JOBYLON_CDN_HOST}/jobs/{self.embed_type}/{self.embed_id}"
            f"/embed/{JOBYLON_LIST_VERSION}/"
        )
        return f"{base}?{urlencode(self.params)}" if self.params else base


@dataclass(frozen=True)
class JobylonJobCard:
    title: str
    job_url: str
    location: str | None


def find_jobylon_embed(soup: BeautifulSoup) -> JobylonEmbed | None:
    """
    Locate the Jobylon widget a career page embeds.

    1) Inline embedder config: ``var jbl_company_id = N;`` / ``var jbl_group_id = N;``
       alongside the cdn.jobylon.com/embedder.js loader, plus optional jbl_filters.
    2) Fallback: a single direct ``<iframe src="https://cdn.jobylon.com/jobs/...">``.

    Returns None when nothing is found or the page is ambiguous. Raises
    JobylonFilterError when filters are present but not parseable.
    """
    configs = _find_config_embeds(soup)
    if configs:
        # Conflicting configs (e.g. company and group ids) are ambiguous.
        return next(iter(configs)) if len(configs) == 1 else None
    return _find_iframe_embed(soup)


def _find_config_embeds(soup: BeautifulSoup) -> set[JobylonEmbed]:
    embeds: set[JobylonEmbed] = set()
    for script in soup.find_all("script"):
        if not isinstance(script, Tag) or script.get("src"):
            continue
        text = _strip_js_comments(script.string or script.get_text())
        if "embedder.js" not in text or JOBYLON_CDN_HOST not in text:
            continue
        ids = {(m.group(1), m.group(2)) for m in _CONFIG_ID_RE.finditer(text)}
        if not ids:
            continue
        filters_match = _FILTERS_RE.search(text)
        filters = _parse_filters(filters_match.group("body")) if filters_match else ()
        embeds |= {
            JobylonEmbed(
                embed_type=_EMBED_TYPES[kind], embed_id=embed_id, params=filters
            )
            for kind, embed_id in ids
        }
    return embeds


def _find_iframe_embed(soup: BeautifulSoup) -> JobylonEmbed | None:
    iframes: set[JobylonEmbed] = set()
    for iframe in soup.find_all("iframe"):
        if not isinstance(iframe, Tag):
            continue
        src = iframe.get("src")
        if isinstance(src, str):
            embed = _embed_from_iframe_src(src)
            if embed:
                iframes.add(embed)
    if len(iframes) == 1:
        return next(iter(iframes))
    return None


def _strip_js_comments(text: str) -> str:
    return _LINE_COMMENT_RE.sub("", _BLOCK_COMMENT_RE.sub("", text))


def _parse_filters(body: str) -> tuple[tuple[str, str], ...]:
    """
    Parse a jbl_filters object literal body, e.g. ``layers_2_ids: [1, 2]``.

    Values are serialised the way the embedder does (encodeURIComponent of the
    JS value), so arrays become comma-joined strings.
    """
    params: list[tuple[str, str]] = []
    entries = [entry for entry in _split_top_level(body) if entry.strip()]
    for entry in entries:
        match = _FILTER_ENTRY_RE.match(entry)
        if not match:
            raise JobylonFilterError(f"unparseable jbl_filters entry: {entry!r}")
        list_body = match.group("list")
        if list_body is not None:
            raw_values = [v for v in list_body.split(",") if v.strip()]
        else:
            raw_values = [match.group("scalar")]
        values = [_parse_filter_value(raw) for raw in raw_values]
        params.append((match.group("key"), ",".join(values)))
    return tuple(params)


def _split_top_level(body: str) -> list[str]:
    """Split on commas that are not inside [...]."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for char in body:
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
        if char == "," and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    parts.append("".join(current))
    return parts


def _parse_filter_value(raw: str) -> str:
    match = _FILTER_VALUE_RE.match(raw)
    if not match:
        raise JobylonFilterError(f"unparseable jbl_filters value: {raw!r}")
    for group in match.groups():
        if group is not None:
            return group
    raise JobylonFilterError(f"unparseable jbl_filters value: {raw!r}")


def _embed_from_iframe_src(src: str) -> JobylonEmbed | None:
    try:
        parsed = urlparse(src if "//" in src else f"https://{src}")
    except ValueError:
        return None
    if (parsed.hostname or "").lower() != JOBYLON_CDN_HOST:
        return None
    match = _EMBED_PATH_RE.match(parsed.path)
    if not match:
        return None
    return JobylonEmbed(
        embed_type=match.group(1),
        embed_id=match.group(2),
        params=tuple(parse_qsl(parsed.query)),
    )


def jobylon_job_url(href: str) -> str | None:
    """Return a canonical emp.jobylon.com job URL, or None if href isn't one."""
    if href.startswith("/jobs/"):
        href = f"https://{JOBYLON_JOBS_HOST}{href}"
    try:
        parsed = urlparse(href)
    except ValueError:
        return None
    if (parsed.hostname or "").lower() != JOBYLON_JOBS_HOST:
        return None
    if not _JOB_PATH_RE.match(parsed.path):
        return None
    return urlunparse(("https", JOBYLON_JOBS_HOST, parsed.path, "", "", ""))


class JobylonScraper(AtsScraper):
    """
    Scrapes career sites that embed the Jobylon jobs widget.

    Jobylon career sites live on custom domains (careers.acme.com) or
    {slug}.jobylon.com, so the board is identified from the inline embedder
    config rather than the URL. Jobs are read from the server-rendered list
    embed: GET https://cdn.jobylon.com/jobs/{companies|company-groups}/{id}/embed/v5/
    Job URLs are the absolute emp.jobylon.com links the embed renders.
    """

    @property
    def source_name(self) -> Source:
        return Source.JOBYLON

    @classmethod
    def supports(cls, *, url: str, soup: BeautifulSoup) -> bool:
        try:
            return find_jobylon_embed(soup) is not None
        except JobylonFilterError:
            # The page is a Jobylon board; find_job_cards logs why it is skipped.
            return True

    def find_job_cards(self, soup: BeautifulSoup) -> list[JobylonJobCard]:
        name = self.__class__.__name__
        try:
            embed = find_jobylon_embed(soup)
        except JobylonFilterError as exc:
            Log.warning(f"{name}: {exc} on {self.career_page.url}; skipping board")
            return []
        if not embed:
            Log.warning(
                f"{name}: no unambiguous Jobylon embed on {self.career_page.url}"
            )
            return []

        list_url = embed.list_url()
        Log.info(f"Fetching {name} jobs from {list_url}")
        try:
            response = self._fetch_page(list_url, return_errors=True)
        except ConnectionError:
            Log.warning(f"{name}: connection error {list_url}")
            return []
        if response is None:
            return []
        if response.status_code != 200:
            Log.warning(f"{name}: failed to fetch {list_url}: {response.status_code}")
            return []

        return self.parse_list_html(response.text)

    @classmethod
    def parse_list_html(cls, html: str) -> list[JobylonJobCard]:
        soup = BeautifulSoup(html, "html.parser")
        cards: list[JobylonJobCard] = []
        for anchor in soup.select("a.js-job"):
            card = cls._parse_anchor(anchor)
            if card:
                cards.append(card)
            else:
                Log.warning(f"{cls.__name__}: skipping job card without title/URL")
        return cards

    @classmethod
    def _parse_anchor(cls, anchor: Tag) -> JobylonJobCard | None:
        href = anchor.get("href")
        job_url = jobylon_job_url(href) if isinstance(href, str) else None
        title_el = anchor.select_one("p.title")
        title = title_el.get_text(" ", strip=True) if title_el else ""
        if not job_url or not title:
            return None

        location: str | None = None
        details = anchor.select_one("p.job-details small")
        if details:
            for strong in details.find_all("strong"):
                strong.extract()  # company name on the card
            text = details.get_text(" ", strip=True).lstrip("|").strip()
            text = _EXTRA_LOCATIONS_RE.sub("", text).strip()
            location = text or None

        return JobylonJobCard(title=title, job_url=job_url, location=location)

    def parse_job_card(self, card: object) -> JobPost | None:
        if not isinstance(card, JobylonJobCard):
            return None

        card_text = " ".join(part for part in (card.title, card.location) if part)
        location, remote_status = self.extract_location_and_remote_status(
            card_text=card_text, location_hint=card.location
        )

        return JobPost(
            title=card.title,
            company_name=self.career_page.company_name,
            company_url=self.career_page.url,
            location=location,
            date_posted=None,
            job_url=card.job_url,
            job_type=None,
            description=None,
            remote_status=remote_status,
            source=self.source_name,
        )
