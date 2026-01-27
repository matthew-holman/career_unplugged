#!/usr/bin/env python3

import argparse

from urllib.parse import urlparse

import requests

URLSCAN_SEARCH_URL = "https://urlscan.io/api/v1/search/"


def extract_first_level(url: str) -> str | None:
    parsed = urlparse(url)

    if not parsed.scheme or not parsed.netloc:
        return None

    path_parts = parsed.path.strip("/").split("/")

    if not path_parts or path_parts[0] == "":
        return f"{parsed.scheme}://{parsed.netloc}"

    return f"{parsed.scheme}://{parsed.netloc}/{path_parts[0]}"


def fetch_urls(domain: str) -> set[str]:

    params = {
        "q": f"domain:{domain}",
        "size": 10000,
    }

    response = requests.get(URLSCAN_SEARCH_URL, params=params)  # type: ignore[arg-type]
    response.raise_for_status()

    data = response.json()
    results = set()

    for entry in data.get("results", []):
        for field in ("task", "page"):
            url = entry.get(field, {}).get("url")
            if not url:
                continue

            normalized = extract_first_level(url)
            if normalized:
                results.add(normalized)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract first-level URLs from urlscan.io results"
    )
    parser.add_argument("domain", help="Domain to query (e.g. jobs.lever.co)")
    args = parser.parse_args()

    urls = fetch_urls(args.domain)

    for url in sorted(urls):
        print(url)


if __name__ == "__main__":
    main()
