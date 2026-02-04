from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app.job_scrapers.ats_scrapers.hibob_scraper import HIBOB_HOST_SUFFIX
from app.job_scrapers.scraper import Source

GREENHOUSE_HOSTS = {"job-boards.greenhouse.io", "job-boards.eu.greenhouse.io"}
HOST_SLUG_SOURCES: dict[str, Source] = {
    "jobs.ashbyhq.com": Source.ASHBY,
    "jobs.lever.co": Source.LEVER,
    "job-boards.greenhouse.io": Source.GREENHOUSE_BOARD,
    "job-boards.eu.greenhouse.io": Source.GREENHOUSE_BOARD,
}
SUFFIX_SOURCES: tuple[tuple[str, Source, bool], ...] = (
    (".teamtailor.com", Source.TEAMTAILOR, True),
    (".recruitee.com", Source.RECRUITEE, False),
    (".personio.com", Source.PERSONIO, False),
    (".personio.de", Source.PERSONIO, False),
    (HIBOB_HOST_SUFFIX, Source.HIBOB, False),
)


@dataclass(frozen=True)
class CareerPageDiscoveryResult:
    url: str
    source: Source


def discover_career_page(
    external_apply_url: str,
) -> CareerPageDiscoveryResult | None:
    try:
        parsed = urlparse(external_apply_url)
    except ValueError:
        return None

    if not parsed.scheme or not parsed.netloc:
        return None

    host = parsed.netloc.lower()
    for suffix, source, trailing_slash in SUFFIX_SOURCES:
        if host.endswith(suffix):
            url = f"https://{host}/" if trailing_slash else f"https://{host}"
            return CareerPageDiscoveryResult(url=url, source=source)

    if host in HOST_SLUG_SOURCES:
        slug = _first_path_segment(parsed.path)
        if not slug:
            return None
        return CareerPageDiscoveryResult(
            url=f"https://{host}/{slug}",
            source=HOST_SLUG_SOURCES[host],
        )

    return None


def extract_slug_from_career_page_url(career_page_url: str) -> str | None:
    try:
        parsed = urlparse(career_page_url)
    except ValueError:
        return None

    if not parsed.netloc:
        return None

    host = parsed.netloc.lower()
    for suffix, _, _ in SUFFIX_SOURCES:
        if host.endswith(suffix):
            base = host[: -len(suffix)]
            return base or None

    if host in HOST_SLUG_SOURCES:
        return _first_path_segment(parsed.path)

    return None


def _first_path_segment(path: str) -> str | None:
    parts = [segment for segment in path.split("/") if segment]
    return parts[0] if parts else None
