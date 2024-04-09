from __future__ import annotations

import re

import requests
import tls_client

from markdownify import markdownify as md
from requests.adapters import HTTPAdapter, Retry

from app.job_scrapers.scraper import JobType


def markdown_converter(description_html: str):
    if description_html is None:
        return None
    markdown = md(description_html)
    return markdown.strip()


def extract_emails_from_text(text: str) -> list[str] | None:
    if not text:
        return None
    email_regex = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    return email_regex.findall(text)


def create_session(
    proxy: dict | None = None,
    is_tls: bool = True,
    has_retry: bool = False,
    delay: int = 1,
) -> requests.Session:
    """
    Creates a requests session with optional tls, proxy, and retry settings.
    :return: A session object
    """
    if is_tls:
        session = tls_client.Session(random_tls_extension_order=True)
        session.proxies = proxy
    else:
        session = requests.Session()
        session.allow_redirects = True
        if proxy:
            session.proxies.update(proxy)
        if has_retry:
            retries = Retry(
                total=3,
                connect=3,
                status=3,
                status_forcelist=[500, 502, 503, 504, 429],
                backoff_factor=delay,
            )
            adapter = HTTPAdapter(max_retries=retries)

            session.mount("http://", adapter)
            session.mount("https://", adapter)
    return session


def get_enum_from_job_type(job_type_str: str) -> JobType | None:
    res = None
    for job_type in JobType:
        if job_type_str in job_type.value:
            res = job_type
    return res
