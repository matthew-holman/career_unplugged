"""URL sources for career page discovery.

Each source takes an ATS domain (e.g. ``jobs.ashbyhq.com``) and an optional
keyword, and returns raw URLs seen on that domain. The discover script turns
them into canonical career page URLs, so a source does not need to know how
any ATS lays out its URLs.

Sources
-------
urlscan
    urlscan.io search API. Pages people (or bots) have scanned.
commoncrawl
    Common Crawl CDX index. Free, no key, and broad for path-based boards
    (Ashby, Greenhouse, Workable). Sites that block crawlers in robots.txt
    (e.g. jobs.lever.co) have nothing indexed.
crtsh
    Certificate Transparency logs via crt.sh. Only useful for subdomain-based
    ATS platforms that issue a certificate per company (e.g. Jobylon);
    platforms using a wildcard certificate expose no company subdomains.
"""

from __future__ import annotations

import json
import time

from collections.abc import Callable
from urllib.parse import unquote, urlparse

import requests

from app.settings import settings

URLSCAN_SEARCH_URL = "https://urlscan.io/api/v1/search/"
COMMON_CRAWL_COLLINFO_URL = "https://index.commoncrawl.org/collinfo.json"
CRT_SH_URL = "https://crt.sh/"

# ATS roots where the company slug is a subdomain ({company}.{root}).
SUBDOMAIN_ATS_ROOTS: tuple[str, ...] = (
    "teamtailor.com",
    "jobs.personio.com",
    "jobs.personio.de",
    "recruitee.com",
    "bamboohr.com",
    "careers.hibob.com",
    "breezy.hr",
    "jobylon.com",
    "peopleforce.io",
)

# Regional apexes a company board can sit under ({company}.na.teamtailor.com).
REGION_HOST_LABELS: frozenset[str] = frozenset({"au", "eu-north", "eu2", "na"})

# Labels that are the ATS vendor's own host (marketing, infra), not a company.
VENDOR_HOST_LABELS: frozenset[str] = frozenset(
    {
        "academy",
        "academy-gcp",
        "admin",
        "analytics",
        "api",
        "app",
        "app-documents",
        "assets",
        "ats",
        "blog",
        "cdn",
        "community",
        "dev",
        "developer",
        "devtest",
        "discover",
        "docs",
        "e",
        "email",
        "errors",
        "ext",
        "feedback",
        "files",
        "finance-integrations",
        "hcm",
        "hello",
        "help",
        "highlights",
        "insights",
        "integrations",
        "kz",
        "landing",
        "lp",
        "mail",
        "media",
        "message",
        "old-blog",
        "onboarding",
        "partner",
        "prod-gcp",
        "prod-kz",
        "prod-uz",
        "relay",
        "roadmap",
        "s",
        "s3",
        "secure",
        "staging",
        "staging-assets",
        "static",
        "status",
        "support",
        "trust",
        "tt",
        "tt-converter",
        "tt-parser-ecs",
        "updates",
        "uz",
        "web",
        "webinar",
    }
)

# Number of most recent Common Crawl crawls to query per domain.
COMMON_CRAWL_CRAWLS = 2

_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 4

UrlSource = Callable[[str, str | None], set[str]]


def bare_domain(domain: str) -> str:
    """Strip any scheme, path and trailing slash from a configured ATS domain."""
    parsed = urlparse(domain if "://" in domain else f"https://{domain}")
    return parsed.netloc.lower()


def _effective_keyword(keyword: str | None) -> str | None:
    """``None`` for no keyword; ``"*"`` (or only wildcards) also means none."""
    if keyword and keyword.strip("*"):
        return keyword.strip("*")
    return None


def _matches_keyword(url: str, keyword: str | None) -> bool:
    return keyword is None or keyword.lower() in unquote(url).lower()


def _get_with_retries(
    url: str,
    params: dict[str, str],
    *,
    timeout: int,
    label: str,
    headers: dict[str, str] | None = None,
) -> requests.Response | None:
    """GET with exponential backoff on transient errors.

    Returns the response for any non-retryable status (callers decide what a
    404 means) or ``None`` once retries are exhausted.
    """
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        except requests.RequestException as exc:
            error = str(exc)
        else:
            if resp.status_code not in _RETRY_STATUSES:
                return resp
            error = f"HTTP {resp.status_code}"
        if attempt < _MAX_ATTEMPTS:
            time.sleep(2**attempt)
    print(f"  [warn] {label}: giving up after {_MAX_ATTEMPTS} attempts ({error})")
    return None


def is_vendor_host(url: str) -> bool:
    """True when a URL on a subdomain-based ATS is the vendor's own host.

    A company board is exactly one label under the root, optionally under a
    regional apex and/or with a ``www.`` prefix: ``acme.teamtailor.com``,
    ``acme.na.teamtailor.com``, ``www.acme.recruitee.com``. Anything else
    (``www.teamtailor.com``, ``status.recruitee.com``, ``ember.cdn.teamtailor.com``)
    belongs to the vendor. Every subdomain on these platforms parses as a career
    page, so without this check vendor hosts get seeded.
    """
    host = urlparse(url).netloc.lower()
    for root in SUBDOMAIN_ATS_ROOTS:
        if host == root:
            return True
        if host.endswith("." + root):
            labels = host[: -(len(root) + 1)].split(".")
            if labels[0] == "www":
                labels = labels[1:]
            if labels and labels[-1] in REGION_HOST_LABELS:
                labels = labels[:-1]
            return len(labels) != 1 or labels[0] in VENDOR_HOST_LABELS
    return False


# ── urlscan.io ──────────────────────────────────────────────────────────────


def fetch_urlscan(domain: str, keyword: str | None, size: int = 500) -> set[str]:
    """Return raw page URLs indexed by urlscan.io for a domain.

    ``keyword`` filters results to pages whose indexed URL contains that string.
    The API key is sent whenever configured: it raises rate limits and the
    result-count ceiling, and is required for wildcard (keyword) queries.
    """
    domain = bare_domain(domain)
    query = f"domain:{domain}"
    effective_keyword = _effective_keyword(keyword)
    if effective_keyword:
        query += f" AND task.url:*{effective_keyword}*"

    headers: dict[str, str] = {}
    if settings.URL_SCAN_API_KEY:
        headers["API-Key"] = settings.URL_SCAN_API_KEY
    elif effective_keyword:
        print(
            "  [error] wildcard keyword queries require a urlscan.io API key. "
            "Set URL_SCAN_API_KEY in your .env file."
        )
        return set()

    resp = _get_with_retries(
        URLSCAN_SEARCH_URL,
        {"q": query, "size": str(size)},
        headers=headers,
        timeout=15,
        label=f"urlscan ({domain})",
    )
    if resp is None:
        return set()
    if not resp.ok:
        print(f"  [warn] urlscan ({domain}): HTTP {resp.status_code}")
        return set()

    urls: set[str] = set()
    for entry in resp.json().get("results", []):
        for field in ("task", "page"):
            url = entry.get(field, {}).get("url", "")
            if url:
                urls.add(url)
    return urls


# ── Common Crawl ────────────────────────────────────────────────────────────

_common_crawl_index_cache: list[str] = []


def _common_crawl_indexes() -> list[str]:
    """CDX API endpoints of the most recent crawls, newest first (cached)."""
    if not _common_crawl_index_cache:
        resp = _get_with_retries(
            COMMON_CRAWL_COLLINFO_URL, {}, timeout=30, label="commoncrawl collinfo"
        )
        if resp is None or not resp.ok:
            return []
        crawls = resp.json()
        _common_crawl_index_cache.extend(
            str(crawl["cdx-api"]) for crawl in crawls[:COMMON_CRAWL_CRAWLS]
        )
    return _common_crawl_index_cache


def _common_crawl_page_count(index_url: str, params: dict[str, str]) -> int:
    resp = _get_with_retries(
        index_url,
        {**params, "showNumPages": "true"},
        timeout=60,
        label=f"commoncrawl pages ({params['url']})",
    )
    if resp is None or not resp.ok:
        return 0
    try:
        return int(resp.json().get("pages", 0))
    except (ValueError, AttributeError):
        return 0


def _parse_cdx_lines(text: str) -> set[str]:
    urls: set[str] = set()
    for line in text.splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict) and isinstance(record.get("url"), str):
            urls.add(record["url"])
    return urls


def fetch_common_crawl(domain: str, keyword: str | None) -> set[str]:
    """Return URLs captured (HTTP 200) on a domain in recent Common Crawls.

    ``keyword`` is matched client-side against the decoded URL, since the
    CDX API has no substring search.
    """
    domain = bare_domain(domain)
    effective_keyword = _effective_keyword(keyword)
    params = {
        "url": domain,
        "matchType": "domain",
        "output": "json",
        "fl": "url",
        "filter": "=status:200",
    }

    urls: set[str] = set()
    for index_url in _common_crawl_indexes():
        pages = _common_crawl_page_count(index_url, params)
        for page in range(pages):
            resp = _get_with_retries(
                index_url,
                {**params, "page": str(page)},
                timeout=90,
                label=f"commoncrawl ({domain} page {page})",
            )
            # 404 means no captures for this domain in this crawl.
            if resp is not None and resp.ok:
                urls.update(_parse_cdx_lines(resp.text))
            time.sleep(1)

    return {url for url in urls if _matches_keyword(url, effective_keyword)}


# ── crt.sh ──────────────────────────────────────────────────────────────────


def fetch_crt_sh(domain: str, keyword: str | None) -> set[str]:
    """Return ``https://{host}`` for each subdomain of a domain in CT logs.

    Only subdomain-based ATS domains are queried; for path-based ones a
    certificate cannot reveal a company slug. Wildcard names are dropped.
    """
    domain = bare_domain(domain)
    if not any(
        root == domain or root.endswith("." + domain) for root in SUBDOMAIN_ATS_ROOTS
    ):
        return set()

    resp = _get_with_retries(
        CRT_SH_URL,
        {"q": f"%.{domain}", "output": "json", "exclude": "expired"},
        timeout=120,
        label=f"crt.sh ({domain})",
    )
    if resp is None or not resp.ok:
        return set()
    try:
        certs = resp.json()
    except ValueError:
        print(f"  [warn] crt.sh ({domain}): response was not JSON")
        return set()

    effective_keyword = _effective_keyword(keyword)
    hosts: set[str] = set()
    for cert in certs if isinstance(certs, list) else []:
        names = cert.get("name_value", "") if isinstance(cert, dict) else ""
        for name in str(names).split():
            host = name.strip().lower().rstrip(".")
            if host.startswith("*.") or not host.endswith("." + domain):
                continue
            if _matches_keyword(host, effective_keyword):
                hosts.add(host)
    return {f"https://{host}" for host in hosts}


SOURCES: dict[str, UrlSource] = {
    "urlscan": fetch_urlscan,
    "commoncrawl": fetch_common_crawl,
    "crtsh": fetch_crt_sh,
}
