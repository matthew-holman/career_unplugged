from __future__ import annotations

from typing import Iterable
from urllib.parse import urlparse

from app.seeds.data.team_tailor_pages import TEAM_TAILOR_PAGE_SEEDS


def normalize_host(value: str) -> str:
    value = value.strip()
    if not value:
        return ""

    # If it's already a bare domain, urlparse treats it as "path"
    if "://" not in value:
        host = value
    else:
        parsed = urlparse(value)
        host = parsed.netloc or parsed.path

    host = host.lower().rstrip("/")

    # Remove potential credentials and port
    host = host.split("@")[-1].split(":")[0]
    return host


def host_to_seed_dict(host: str) -> dict:
    """
    Convert a host like 'saltx.teamtailor.com' or 'foo.na.teamtailor.com'
    into the seed dict format:
      {
        "company_name": "<subdomain part>",
        "url": "https://<host>",
        "active": True,
      }
    company_name is derived from the left-most label (the subdomain).
    """
    host = normalize_host(host)
    if not host:
        raise ValueError("Empty host")

    company_name = host.split(".", 1)[0]  # left-most label only
    return {
        "company_name": company_name,
        "url": f"https://{host}",
        "active": True,
    }


def diff_seed_dicts(
    seeds: list[dict],
    google_domains: Iterable[str],
) -> list[dict]:
    seed_hosts = {normalize_host(item["url"]) for item in seeds if item.get("url")}
    google_hosts = {normalize_host(d) for d in google_domains if normalize_host(d)}

    missing_hosts = sorted(google_hosts - seed_hosts)
    return [host_to_seed_dict(host) for host in missing_hosts]


google_domains_text = """\
1889pizza.teamtailor.com
"""


def main():
    google_domains = [line for line in google_domains_text.splitlines() if line.strip()]
    missing_seed_dicts = diff_seed_dicts(TEAM_TAILOR_PAGE_SEEDS, google_domains)
    print(f"Missing ({len(missing_seed_dicts)}):")
    for item in missing_seed_dicts:
        print(str(item) + ",")


if __name__ == "__main__":
    main()
