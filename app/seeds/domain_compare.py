from __future__ import annotations

from typing import Iterable
from urllib.parse import urlparse

from app.seeds.career_pages import SEED_LISTS


def key_to_seed_dict(key: str) -> dict:
    """
    key is canonical host+path, e.g.:
      - "panmacmillan.teamtailor.com"
      - "job-boards.eu.greenhouse.io/wunderflats"
    """
    key = key.strip().lstrip("/")
    if not key:
        raise ValueError("Empty url key")

    if "/" in key:
        host, path = key.split("/", 1)
        company_name = path.split("/")[-1]  # last segment
        url = f"https://{host}/{path}"
    else:
        host = key
        company_name = host.split(".", 1)[0]  # left-most label
        url = f"https://{host}"

    return {
        "company_name": company_name,
        "url": url,
        "active": True,
    }


def normalize_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""

    # Ensure urlparse puts the host in netloc
    if "://" not in value:
        value = "https://" + value

    parsed = urlparse(value)

    host = (parsed.netloc or "").lower()

    # Remove potential credentials and port
    host = host.split("@")[-1].split(":")[0]

    path = (parsed.path or "").rstrip("/")

    # Canonical form: host + path (no scheme, no query, no fragment)
    return f"{host}{path}"


def diff_seed_dicts(
    seeds: list[dict],
    google_domains: Iterable[str],
) -> list[dict]:
    seed_keys = {normalize_url(item["url"]) for item in seeds if item.get("url")}
    google_keys = {normalize_url(d) for d in google_domains if normalize_url(d)}

    missing_hosts = sorted(google_keys - seed_keys)
    # intersection = google_keys.intersection(seed_keys)
    return [key_to_seed_dict(host) for host in missing_hosts]


google_domains_text = """\
job-boards.eu.greenhouse.io/algoquant
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
