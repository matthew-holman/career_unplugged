import json

import pytest
import requests_mock

from app.seeds import discover_career_pages, discovery_sources
from app.seeds.discovery_sources import (
    COMMON_CRAWL_COLLINFO_URL,
    CRT_SH_URL,
    bare_domain,
    fetch_common_crawl,
    fetch_crt_sh,
    is_vendor_host,
)

CC_INDEX = "https://index.commoncrawl.org/CC-MAIN-2026-47-index"


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(discovery_sources.time, "sleep", lambda _: None)
    monkeypatch.setattr(discover_career_pages.time, "sleep", lambda _: None)
    discovery_sources._common_crawl_index_cache.clear()


def _cdx(*urls: str) -> str:
    return "\n".join(json.dumps({"url": url}) for url in urls)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.teamtailor.com", True),
        ("https://teamtailor.com", True),
        ("https://status.recruitee.com", True),
        ("https://api.eu-north.teamtailor.com", True),
        ("https://na.teamtailor.com", True),
        ("https://ember.cdn.teamtailor.com", True),
        ("https://relay.app.bamboohr.com", True),
        ("https://acme.teamtailor.com/", False),
        ("https://spokeo.na.teamtailor.com", False),
        ("https://www.acme.na.teamtailor.com", False),
        ("https://www.acme.recruitee.com", False),
        ("https://acme.jobs.personio.de", False),
        ("https://acme.careers.hibob.com", False),
        ("https://jobs.ashbyhq.com/acme", False),
    ],
)
def test_is_vendor_host(url: str, expected: bool) -> None:
    assert is_vendor_host(url) is expected


def test_bare_domain_strips_scheme_and_path() -> None:
    assert bare_domain("https://jobs.deel.com/") == "jobs.deel.com"
    assert bare_domain("teamtailor.com") == "teamtailor.com"


def test_fetch_crt_sh_returns_hosts_without_wildcards() -> None:
    certs = [
        {"name_value": "*.jobylon.com\njobylon.com"},
        {"name_value": "acme.jobylon.com"},
        {"name_value": "Beta.jobylon.com\nacme.jobylon.com"},
        {"name_value": "other.example.com"},
    ]
    with requests_mock.Mocker() as m:
        m.get(CRT_SH_URL, json=certs)
        urls = fetch_crt_sh("jobylon.com", None)
    assert urls == {"https://acme.jobylon.com", "https://beta.jobylon.com"}


def test_fetch_crt_sh_skips_path_based_domains() -> None:
    with requests_mock.Mocker() as m:
        assert fetch_crt_sh("jobs.ashbyhq.com", None) == set()
        assert not m.called


def test_fetch_crt_sh_retries_then_gives_up() -> None:
    with requests_mock.Mocker() as m:
        m.get(CRT_SH_URL, status_code=502)
        assert fetch_crt_sh("jobylon.com", None) == set()
        assert m.call_count == discovery_sources._MAX_ATTEMPTS


def test_fetch_common_crawl_pages_and_filters_keyword() -> None:
    with requests_mock.Mocker() as m:
        m.get(COMMON_CRAWL_COLLINFO_URL, json=[{"cdx-api": CC_INDEX}])
        m.get(
            f"{CC_INDEX}?showNumPages=true",
            complete_qs=False,
            json={"pages": 2},
        )
        m.get(
            f"{CC_INDEX}?page=0",
            complete_qs=False,
            text=_cdx("https://jobs.ashbyhq.com/acme/1?loc=malm%C3%B6") + "\n<html>",
        )
        m.get(
            f"{CC_INDEX}?page=1",
            complete_qs=False,
            text=_cdx("https://jobs.ashbyhq.com/beta/2?loc=berlin"),
        )
        everything = fetch_common_crawl("jobs.ashbyhq.com", None)
        malmo = fetch_common_crawl("jobs.ashbyhq.com", "malmö")

    assert everything == {
        "https://jobs.ashbyhq.com/acme/1?loc=malm%C3%B6",
        "https://jobs.ashbyhq.com/beta/2?loc=berlin",
    }
    assert malmo == {"https://jobs.ashbyhq.com/acme/1?loc=malm%C3%B6"}


def test_discover_merges_sources_and_drops_vendor_hosts() -> None:
    sources = {
        "a": lambda domain, keyword: {
            "https://acme.teamtailor.com/jobs/1",
            "https://www.teamtailor.com/pricing",
        },
        "b": lambda domain, keyword: {
            "https://acme.teamtailor.com",
            "https://beta.teamtailor.com",
            "https://known.teamtailor.com",
        },
    }
    found = discover_career_pages.discover(
        [("teamtailor.com", "team_tailor_pages.py")],
        None,
        {"https://known.teamtailor.com"},
        supported=True,
        sources=sources,
    )
    assert sorted(url for url, _, _ in found["team_tailor_pages.py"]) == [
        "https://acme.teamtailor.com",
        "https://beta.teamtailor.com",
    ]
