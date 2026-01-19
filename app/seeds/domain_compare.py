from __future__ import annotations

from typing import Iterable
from urllib.parse import urlparse

from app.seeds.career_pages import SEED_LISTS


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

    company_name = host.split("/", 1)[1]
    # company_name = host.split(".", 1)[0]  # left-most label only
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
    # intersection = google_hosts.intersection(seed_hosts)
    return [host_to_seed_dict(host) for host in missing_hosts]


google_domains_text = """\
job-boards.greenhouse.io/akuity
job-boards.greenhouse.io/algoquant
job-boards.greenhouse.io/alpaca
job-boards.greenhouse.io/amenitiz
job-boards.greenhouse.io/bioptimus8
job-boards.greenhouse.io/bitmex
job-boards.greenhouse.io/bitwarden
job-boards.greenhouse.io/canonicaljobs
job-boards.greenhouse.io/coinbase
job-boards.greenhouse.io/connectwise
job-boards.greenhouse.io/consensys
job-boards.greenhouse.io/correlationone
job-boards.greenhouse.io/doitintl
job-boards.greenhouse.io/echodynecorp
job-boards.greenhouse.io/elementbiosciences
job-boards.greenhouse.io/gitlab
job-boards.greenhouse.io/ketryx
job-boards.greenhouse.io/nansen
job-boards.greenhouse.io/neo4j
job-boards.greenhouse.io/offensivesecurity
job-boards.greenhouse.io/onapsis
job-boards.greenhouse.io/planetscale
job-boards.greenhouse.io/qualio
job-boards.greenhouse.io/quanthealth
job-boards.greenhouse.io/realchemistry
job-boards.greenhouse.io/realtimeboardglobal
job-boards.greenhouse.io/remotecom
job-boards.greenhouse.io/remotereferralboardinternaluseonly
job-boards.greenhouse.io/storyblok
job-boards.greenhouse.io/sustainabletalent
job-boards.greenhouse.io/taboola
job-boards.greenhouse.io/thrivecart
job-boards.greenhouse.io/vaayutech
job-boards.greenhouse.io/veza
job-boards.greenhouse.io/wakam
job-boards.greenhouse.io/yld
"""


def main():
    google_domains = [line for line in google_domains_text.splitlines() if line.strip()]
    master_list = [page for page_list in SEED_LISTS for page in page_list]
    missing_seed_dicts: list[dict] = diff_seed_dicts(master_list, google_domains)
    print(f"Missing ({len(missing_seed_dicts)}):")
    for item in missing_seed_dicts:
        print(str(item) + ",")


if __name__ == "__main__":
    main()
