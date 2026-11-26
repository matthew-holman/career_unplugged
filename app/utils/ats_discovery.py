from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app.job_scrapers.ats_scrapers.bamboohr_scraper import BAMBOO_HOST_SUFFIX
from app.job_scrapers.ats_scrapers.hibob_scraper import HIBOB_HOST_SUFFIX
from app.job_scrapers.ats_scrapers.jobylon_scraper import (
    JOBYLON_HOST_SUFFIX,
    JOBYLON_RESERVED_HOSTS,
)
from app.job_scrapers.ats_scrapers.recruitee_scraper import RECRUITEE_HOST_SUFFIX
from app.job_scrapers.ats_scrapers.workable_scraper import (
    WORKABLE_HOST,
    WORKABLE_RESERVED_SEGMENTS,
)
from app.job_scrapers.scraper import Source

GREENHOUSE_HOSTS = {"job-boards.greenhouse.io", "job-boards.eu.greenhouse.io"}
HOST_SLUG_SOURCES: dict[str, Source] = {
    "jobs.ashbyhq.com": Source.ASHBY,
    "jobs.lever.co": Source.LEVER,
    "job-boards.greenhouse.io": Source.GREENHOUSE_BOARD,
    "job-boards.eu.greenhouse.io": Source.GREENHOUSE_BOARD,
    WORKABLE_HOST: Source.WORKABLE,
}
# Path segments that are never a company slug, per host.
RESERVED_SLUG_SEGMENTS: dict[str, frozenset[str]] = {
    WORKABLE_HOST: WORKABLE_RESERVED_SEGMENTS,
}
SUFFIX_SOURCES: tuple[tuple[str, Source, bool], ...] = (
    (".teamtailor.com", Source.TEAMTAILOR, True),
    (RECRUITEE_HOST_SUFFIX, Source.RECRUITEE, False),
    (".personio.com", Source.PERSONIO, False),
    (".personio.de", Source.PERSONIO, False),
    (HIBOB_HOST_SUFFIX, Source.HIBOB, False),
    (BAMBOO_HOST_SUFFIX, Source.BAMBOO, False),
    (JOBYLON_HOST_SUFFIX, Source.JOBYLON, False),
)
# Hosts under a SUFFIX_SOURCES suffix that belong to the ATS itself, not to a
# company board (e.g. emp.jobylon.com, where LinkedIn apply links point).
RESERVED_HOSTS: frozenset[str] = JOBYLON_RESERVED_HOSTS


# First host label of a company's own careers site: careers.acme.com.
CAREER_HOST_LABELS: frozenset[str] = frozenset(
    {
        "career",
        "careers",
        "job",
        "jobb",
        "jobs",
        "join",
        "joinus",
        "karriere",
        "karriar",
        "recruiting",
        "talent",
        "vacancies",
        "work",
        "workwithus",
    }
)
# Path segment of a company's careers section: acme.com/careers.
CAREER_PATH_SEGMENTS: frozenset[str] = frozenset(
    {
        "career",
        "careers",
        "join-us",
        "joinus",
        "jobb",
        "jobs",
        "karriar",
        "karriere",
        "lediga-jobb",
        "open-positions",
        "stellenangebote",
        "vacancies",
        "work-with-us",
    }
)
# How deep into the path a careers segment may sit (/en/careers counts).
_MAX_CAREER_SEGMENT_DEPTH = 2
# Hosts shared by many companies (ATS vendors, job boards). A careers-like host
# label or path on these names the vendor, not a company site.
SHARED_JOB_HOST_DOMAINS: frozenset[str] = frozenset(
    {
        "adp.com",
        "ashbyhq.com",
        "bamboohr.com",
        "breezy.hr",
        "dover.com",
        "glassdoor.com",
        "greenhouse.io",
        "hibob.com",
        "icims.com",
        "indeed.com",
        "jobvite.com",
        "jobylon.com",
        "join.com",
        "lever.co",
        "linkedin.com",
        "myworkdayjobs.com",
        "myworkdaysite.com",
        "oraclecloud.com",
        "personio.com",
        "personio.de",
        "pinpointhq.com",
        "recruitee.com",
        "rippling.com",
        "smartrecruiters.com",
        "stepstone.de",
        "successfactors.com",
        "successfactors.eu",
        "taleo.net",
        "teamtailor.com",
        "ultipro.com",
        "welcometothejungle.com",
        "workable.com",
    }
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
    if host in RESERVED_HOSTS:
        return None
    for suffix, source, trailing_slash in SUFFIX_SOURCES:
        if host.endswith(suffix):
            url = f"https://{host}/" if trailing_slash else f"https://{host}"
            return CareerPageDiscoveryResult(url=url, source=source)

    if host in HOST_SLUG_SOURCES:
        slug = _first_path_segment(parsed.path)
        if not slug or _is_reserved_segment(host, slug):
            return None
        return CareerPageDiscoveryResult(
            url=f"https://{host}/{slug}",
            source=HOST_SLUG_SOURCES[host],
        )

    return None


def discover_custom_career_page(external_apply_url: str) -> str | None:
    """Guess a company's own careers page from a job URL off the known ATS hosts.

    ``careers.acme.com/jobs/123`` gives ``https://careers.acme.com`` and
    ``acme.com/en/careers/123`` gives ``https://acme.com/en/careers``. Returns
    None when the URL does not look like a careers site, or is on a shared ATS
    or job board host. Whether a scraper can read the page is only known once
    the ATS sync fetches it.
    """
    try:
        parsed = urlparse(external_apply_url)
        host = (parsed.hostname or "").lower()
    except ValueError:
        return None

    if parsed.scheme not in {"http", "https"} or not host:
        return None
    if _is_shared_job_host(host):
        return None

    labels = host.split(".")
    if labels[0] == "www":
        labels = labels[1:]
    if len(labels) >= 3 and labels[0] in CAREER_HOST_LABELS:
        return f"https://{host}"

    segments = [segment for segment in parsed.path.split("/") if segment]
    for depth, segment in enumerate(segments[:_MAX_CAREER_SEGMENT_DEPTH]):
        if segment.lower() in CAREER_PATH_SEGMENTS:
            path = "/".join(segments[: depth + 1])
            return f"https://{host}/{path}"

    return None


def extract_slug_from_career_page_url(career_page_url: str) -> str | None:
    try:
        parsed = urlparse(career_page_url)
    except ValueError:
        return None

    if not parsed.netloc:
        return None

    host = parsed.netloc.lower()
    if host in RESERVED_HOSTS:
        return None
    for suffix, _, _ in SUFFIX_SOURCES:
        if host.endswith(suffix):
            base = host[: -len(suffix)]
            return base or None

    if host in HOST_SLUG_SOURCES:
        slug = _first_path_segment(parsed.path)
        if not slug or _is_reserved_segment(host, slug):
            return None
        return slug

    return None


def _first_path_segment(path: str) -> str | None:
    parts = [segment for segment in path.split("/") if segment]
    return parts[0] if parts else None


def _is_reserved_segment(host: str, segment: str) -> bool:
    return segment.lower() in RESERVED_SLUG_SEGMENTS.get(host, frozenset())


def _is_shared_job_host(host: str) -> bool:
    return any(
        host == domain or host.endswith(f".{domain}")
        for domain in SHARED_JOB_HOST_DOMAINS
    )
