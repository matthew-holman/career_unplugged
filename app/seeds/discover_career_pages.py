#!/usr/bin/env python3
"""Discover new career pages on known ATS platforms.

Runs three stages in order:

1. Discover: query each URL source (urlscan.io, Common Crawl, crt.sh; see
   ``app.seeds.discovery_sources``) for URLs on each ATS domain,
   canonicalise them, drop vendor hosts and any page already in a seed file.
2. Write: append the new pages to their seed files in app/seeds/data/.
3. Seed: insert the new supported-ATS pages into the database (what
   ``app.workers.seed_career_pages`` does, for just the new pages).

Pages on unsupported ATS platforms are written to their seed files but not
seeded, since no scraper can sync them yet. A high count there marks a good
candidate for a new scraper.

Usage
-----
    # All supported platforms: discover, update seed files, seed the database
    poetry run python -m app.seeds.discover_career_pages

    # Only print what would be added; change nothing
    poetry run python -m app.seeds.discover_career_pages --dry-run

    # Update seed files but leave the database alone
    poetry run python -m app.seeds.discover_career_pages --skip-db

    # Add unsupported platforms too (surfaces new scraper candidates)
    poetry run python -m app.seeds.discover_career_pages --all

    # Narrow results to a specific city/keyword appearing in the indexed URL
    poetry run python -m app.seeds.discover_career_pages --keyword gothenburg
    poetry run python -m app.seeds.discover_career_pages --keyword malmö

    # Only some sources (default: all)
    poetry run python -m app.seeds.discover_career_pages --source commoncrawl
    poetry run python -m app.seeds.discover_career_pages --source crtsh --source urlscan

    # Single ATS domain only
    poetry run python -m app.seeds.discover_career_pages --domain teamtailor.com
"""

from __future__ import annotations

import argparse
import time

from collections import defaultdict
from typing import cast
from urllib.parse import urlparse

from app.db.db import get_db
from app.seeds.career_pages import CareerPageSeeder
from app.seeds.data.ashby_pages import ASHBY_PAGE_SEEDS
from app.seeds.data.bamboo_pages import BAMBOO_PAGE_SEEDS
from app.seeds.data.breezy_pages import BREEZY_PAGE_SEEDS
from app.seeds.data.career_pages import CAREER_PAGE_SEEDS
from app.seeds.data.deel_pages import DEEL_PAGE_SEEDS
from app.seeds.data.dover_pages import DOVER_PAGE_SEEDS
from app.seeds.data.greenhouse_pages import GREENHOUSE_PAGE_SEEDS
from app.seeds.data.hibob_pages import HIBOB_PAGE_SEEDS
from app.seeds.data.hirefly_pages import BREEZY_PAGE_SEEDS as HIREFLY_PAGE_SEEDS
from app.seeds.data.jobylon_pages import JOBYLON_PAGE_SEEDS
from app.seeds.data.join_pages import JOIN_PAGE_SEEDS
from app.seeds.data.lever_pages import LEVER_PAGE_SEEDS
from app.seeds.data.people_force_pages import PEOPLE_FORCE_PAGE_SEEDS
from app.seeds.data.personio_pages import PERSONIO_PAGE_SEEDS
from app.seeds.data.recruitee_pages import RECRUITEE_PAGE_SEEDS
from app.seeds.data.rippling_pages import RIPPLING_PAGE_SEEDS
from app.seeds.data.sloneek_pages import SLONEEK_PAGE_SEEDS
from app.seeds.data.team_tailor_pages import TEAM_TAILOR_PAGE_SEEDS
from app.seeds.data.workable_pages import WORKABLE_PAGE_SEEDS
from app.seeds.discovery_sources import (
    SOURCES,
    SUBDOMAIN_ATS_ROOTS,
    UrlSource,
    is_vendor_host,
)
from app.seeds.seed_file_writer import SeedEntry, SeedFileError, append_seed_entries
from app.utils.ats_discovery import discover_career_page

# ATS platforms that have a scraper in app/job_scrapers/ats_scrapers/.
# Tuple: (urlscan_query_domain, seed_file_hint)
SUPPORTED_ATS: list[tuple[str, str]] = [
    ("teamtailor.com", "team_tailor_pages.py"),
    ("jobs.ashbyhq.com", "ashby_pages.py"),
    ("jobs.lever.co", "lever_pages.py"),
    ("jobs.eu.lever.co", "lever_pages.py"),
    ("job-boards.greenhouse.io", "greenhouse_pages.py"),
    ("job-boards.eu.greenhouse.io", "greenhouse_pages.py"),
    ("jobs.personio.com", "personio_pages.py"),
    ("jobs.personio.de", "personio_pages.py"),
    ("recruitee.com", "recruitee_pages.py"),
    ("bamboohr.com", "bamboo_pages.py"),
    ("hibob.com", "hibob_pages.py"),
    ("apply.workable.com", "workable_pages.py"),
    # Only {company}.jobylon.com boards are found here; boards embedded on a
    # company's own domain have to be added by hand.
    ("jobylon.com", "jobylon_pages.py"),
]

# ATS platforms that have seed files but no scraper yet.
# Discovering more companies here helps prioritise which scraper to build next.
UNSUPPORTED_ATS: list[tuple[str, str]] = [
    ("app.dover.com", "dover_pages.py"),
    ("breezy.hr", "breezy_pages.py"),
    ("join.com", "join_pages.py"),
    ("peopleforce.io", "people_force_pages.py"),
    ("jobs.sloneek.com", "sloneek_pages.py"),
    ("hireflyapp.com", "hirefly_pages.py"),
    ("https://jobs.deel.com/", "deel_pages.py"),
]

ALL_SEED_LISTS = [
    ASHBY_PAGE_SEEDS,
    BAMBOO_PAGE_SEEDS,
    BREEZY_PAGE_SEEDS,
    CAREER_PAGE_SEEDS,
    DEEL_PAGE_SEEDS,
    DOVER_PAGE_SEEDS,
    GREENHOUSE_PAGE_SEEDS,
    HIBOB_PAGE_SEEDS,
    HIREFLY_PAGE_SEEDS,
    JOBYLON_PAGE_SEEDS,
    JOIN_PAGE_SEEDS,
    LEVER_PAGE_SEEDS,
    PEOPLE_FORCE_PAGE_SEEDS,
    PERSONIO_PAGE_SEEDS,
    RECRUITEE_PAGE_SEEDS,
    RIPPLING_PAGE_SEEDS,
    SLONEEK_PAGE_SEEDS,
    TEAM_TAILOR_PAGE_SEEDS,
    WORKABLE_PAGE_SEEDS,
]


def _build_existing_urls() -> set[str]:
    """All URLs already present in any seed file, normalised."""
    return {
        cast(str, seed["url"]).rstrip("/")
        for seed_list in ALL_SEED_LISTS
        for seed in seed_list
    }


def _canonical_supported(raw_url: str) -> str | None:
    """
    Use ats_discovery to extract the canonical career page URL.
    Returns None if the URL is not recognised as a supported ATS.
    """
    result = discover_career_page(raw_url)
    return result.url.rstrip("/") if result else None


# Subdomain-based unsupported ATS: the company slug IS the subdomain.
_UNSUPPORTED_SUBDOMAIN_ROOTS: frozenset[str] = frozenset(
    {"breezy.hr", "peopleforce.io"}
)

# Path-based unsupported ATS where the first path segment is the company slug.
_UNSUPPORTED_PATH_ROOTS: frozenset[str] = frozenset({"app.dover.com", "hireflyapp.com"})


def _canonical_unsupported(raw_url: str, query_domain: str) -> str | None:
    """
    Best-effort canonical URL for unsupported ATS platforms.

    For path-based platforms (apply.workable.com, join.com, …) returns
    scheme + host + /company-slug.
    For subdomain-based platforms (breezy.hr, peopleforce.io, …) returns
    scheme + host (the subdomain IS the company identifier).
    """
    try:
        parsed = urlparse(raw_url)
    except ValueError:
        return None

    if not parsed.scheme or not parsed.netloc:
        return None

    host = parsed.netloc.lower()
    parts = [p for p in parsed.path.strip("/").split("/") if p]

    for root in _UNSUPPORTED_SUBDOMAIN_ROOTS:
        if host.endswith("." + root):
            return f"https://{host}"

    if host in _UNSUPPORTED_PATH_ROOTS:
        return f"https://{host}/{parts[0]}" if parts else None

    if host == "join.com":
        if len(parts) >= 2 and parts[0] == "companies":
            return f"https://join.com/companies/{parts[1]}"
        return None

    if host == "jobs.sloneek.com":
        return (
            f"https://jobs.sloneek.com/{parts[0]}/{parts[1]}"
            if len(parts) >= 2
            else None
        )

    return None


def _company_slug(canonical_url: str) -> str:
    """Extract a human-readable company slug from a canonical career page URL."""
    try:
        parsed = urlparse(canonical_url)
    except ValueError:
        return canonical_url

    host = parsed.netloc.lower()

    # For subdomain-based: strip the ATS root, use leftmost subdomain label.
    for root in SUBDOMAIN_ATS_ROOTS:
        if host.endswith("." + root):
            subdomain = host[: -(len(root) + 1)]
            # Take the leftmost label (ignore www / careers prefix)
            return subdomain.split(".")[-1]

    # For path-based: first path segment is the slug.
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if parts:
        # join.com and sloneek have two-segment paths — use the last meaningful one
        slug = (
            parts[-1] if parts[-1] not in ("companies", "ats-v2", "jobs") else parts[0]
        )
        return slug

    return host


def _fetch_all_sources(
    domain: str, keyword: str | None, sources: dict[str, UrlSource]
) -> set[str]:
    """Union of raw URLs from every selected source for one ATS domain."""
    raw_urls: set[str] = set()
    for name, fetch in sources.items():
        print(f"  Scanning {domain} via {name}...", end=" ", flush=True)
        urls = fetch(domain, keyword)
        print(f"{len(urls)} raw URLs")
        raw_urls |= urls
        # Be polite to free tiers between sources and domains
        time.sleep(1)
    return raw_urls


def discover(
    ats_list: list[tuple[str, str]],
    keyword: str | None,
    existing: set[str],
    *,
    supported: bool,
    sources: dict[str, UrlSource] | None = None,
) -> dict[str, list[tuple[str, str, str]]]:
    """
    For each ATS domain, fetch URLs from each source and return new career pages.

    Returns a dict keyed by seed_file_hint → list of (canonical_url, slug, query_domain).
    """
    sources = SOURCES if sources is None else sources
    found: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    seen_canonicals: set[str] = set(existing)

    for query_domain, seed_file in ats_list:
        for raw in _fetch_all_sources(query_domain, keyword, sources):
            if supported:
                canonical = _canonical_supported(raw)
            else:
                canonical = _canonical_unsupported(raw, query_domain)

            if not canonical or is_vendor_host(canonical):
                continue

            canonical = canonical.rstrip("/")
            if canonical in seen_canonicals:
                continue

            seen_canonicals.add(canonical)
            slug = _company_slug(canonical)
            found[seed_file].append((canonical, slug, query_domain))

    return found


_DIVIDER = "=" * 60


def _print_supported(results: dict[str, list[tuple[str, str, str]]]) -> None:
    total = sum(len(v) for v in results.values())
    print(f"\n{_DIVIDER}")
    print(f"SUPPORTED ATS — {total} new career pages")
    print("Seed file entries to add")
    print(_DIVIDER)
    for seed_file, entries in sorted(results.items()):
        if not entries:
            continue
        print(f"\n# ── {seed_file} ({len(entries)} new) ──")
        for canonical, slug, _ in sorted(entries, key=lambda x: x[1]):
            print(
                f'    {{"company_name": "{slug}", "url": "{canonical}", "active": True}},'
            )


def _print_unsupported(results: dict[str, list[tuple[str, str, str]]]) -> None:
    total = sum(len(v) for v in results.values())
    print(f"\n{_DIVIDER}")
    print(f"UNSUPPORTED ATS — {total} new career pages (no scraper yet)")
    print("High count = good candidate for a new scraper")
    print(_DIVIDER)
    for seed_file, entries in sorted(results.items(), key=lambda kv: -len(kv[1])):
        if not entries:
            continue
        domain = entries[0][2] if entries else "?"
        print(f"\n# ── {domain} → {seed_file} ({len(entries)} new) ──")
        for canonical, slug, _ in sorted(entries, key=lambda x: x[1]):
            print(
                f'    {{"company_name": "{slug}", "url": "{canonical}", "active": True}},'
            )


DiscoveryResults = dict[str, list[tuple[str, str, str]]]


def write_seed_files(results: DiscoveryResults) -> dict[str, list[SeedEntry]]:
    """Stage 2: append discovered pages to their seed files."""
    written: dict[str, list[SeedEntry]] = {}
    for seed_file, found in sorted(results.items()):
        entries = [SeedEntry(company_name=slug, url=url) for url, slug, _ in found]
        try:
            added = append_seed_entries(seed_file, entries)
        except SeedFileError as exc:
            print(f"  [error] {exc}; {seed_file} left unchanged")
            continue
        if added:
            print(f"  {seed_file}: +{len(added)}")
            written[seed_file] = added
    return written


def seed_database(entries: list[SeedEntry]) -> int:
    """Stage 3: insert the new pages into the database. Returns pages created."""
    with next(get_db()) as db_session:
        created = CareerPageSeeder(db_session).seed(e.as_seed() for e in entries)
        db_session.commit()
    return created


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Discover new career pages on known ATS platforms via urlscan.io, "
            "Common Crawl and crt.sh, "
            "add them to the seed files and seed the database"
        )
    )
    parser.add_argument(
        "--domain",
        help="Limit to a single ATS domain (e.g. teamtailor.com)",
    )
    parser.add_argument(
        "--keyword",
        help=(
            "Only keep URLs containing this keyword " "(e.g. gothenburg, malmö, sweden)"
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="include_unsupported",
        help="Also scan unsupported ATS domains to surface new scraper candidates",
    )
    parser.add_argument(
        "--source",
        action="append",
        choices=sorted(SOURCES),
        dest="sources",
        help=(
            "URL source to query; repeat to use several "
            "(default: all of %(choices)s)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print discovered pages; do not touch seed files or the database",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Update seed files but do not seed the database",
    )
    return parser.parse_args()


def _select_ats(
    args: argparse.Namespace,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    supported_ats = SUPPORTED_ATS
    unsupported_ats = UNSUPPORTED_ATS if args.include_unsupported else []
    if args.domain:
        supported_ats = [(d, f) for d, f in SUPPORTED_ATS if d == args.domain]
        unsupported_ats = [(d, f) for d, f in UNSUPPORTED_ATS if d == args.domain]
    return supported_ats, unsupported_ats


def main() -> None:
    args = _parse_args()
    supported_ats, unsupported_ats = _select_ats(args)
    if not supported_ats and not unsupported_ats:
        print(f"Domain '{args.domain}' not found in either ATS list.")
        return

    sources = {name: SOURCES[name] for name in args.sources or SOURCES}
    existing = _build_existing_urls()
    print(f"Loaded {len(existing)} existing seed URLs")
    print(f"Sources: {', '.join(sources)}")
    print(f"Keyword filter: {args.keyword!r}\n")

    # Stage 1: discover
    supported_results: DiscoveryResults = {}
    unsupported_results: DiscoveryResults = {}
    if supported_ats:
        print("Scanning supported ATS platforms...")
        supported_results = discover(
            supported_ats, args.keyword, existing, supported=True, sources=sources
        )
        _print_supported(supported_results)
    if unsupported_ats:
        print("\nScanning unsupported ATS platforms...")
        unsupported_results = discover(
            unsupported_ats,
            args.keyword,
            existing,
            supported=False,
            sources=sources,
        )
        _print_unsupported(unsupported_results)

    if args.dry_run:
        print("\nDry run: seed files and database left unchanged.")
        return

    # Stage 2: write seed files
    print(f"\n{_DIVIDER}\nUpdating seed files\n{_DIVIDER}")
    written_supported = write_seed_files(supported_results)
    write_seed_files(unsupported_results)

    # Stage 3: seed the database (supported platforms only)
    new_supported = [e for entries in written_supported.values() for e in entries]
    if args.skip_db or not new_supported:
        reason = "--skip-db" if args.skip_db else "no new supported pages"
        print(f"\nDatabase not seeded ({reason}).")
        return
    created = seed_database(new_supported)
    print(f"\nSeeded {created} new career pages into the database.")


if __name__ == "__main__":
    main()
