from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.job_analysis.description_extractor import DescriptionExtractor
from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.ats_scrapers.workable_scraper import (
    WORKABLE_HOST,
    workable_account_slug,
)
from app.job_scrapers.scraper import Source
from app.log import Log
from app.models import Job

_DESCRIPTION_SECTIONS = ("description", "requirements", "benefits")


class Workable(DescriptionExtractor):
    """
    Workable job pages are a JS app, so the description comes from the job API:
    GET https://apply.workable.com/api/v2/accounts/{slug}/jobs/{shortcode}
    """

    source = Source.WORKABLE

    @staticmethod
    def extract_description(soup: BeautifulSoup, job: Job) -> str:
        if not job.ats_source_url:
            return ""

        api_url = Workable.build_api_url(job.ats_source_url)
        if not api_url:
            Log.warning(
                "Workable description extractor: cannot build API URL for "
                f"{job.ats_source_url}"
            )
            return ""

        response = AtsScraper._fetch_page(api_url)
        if not response:
            return ""

        try:
            payload: object = response.json()
        except ValueError:
            Log.warning(f"Workable description extractor: invalid JSON from {api_url}")
            return ""

        return Workable.description_from_payload(payload)

    @staticmethod
    def build_api_url(job_url: str) -> str | None:
        slug = workable_account_slug(job_url)
        if not slug:
            return None
        parts = [segment for segment in urlparse(job_url).path.split("/") if segment]
        # Expected path: /{slug}/j/{shortcode}/
        if len(parts) < 3 or parts[1] != "j":
            return None
        shortcode = parts[2]
        return f"https://{WORKABLE_HOST}/api/v2/accounts/{slug}/jobs/{shortcode}"

    @staticmethod
    def description_from_payload(payload: object) -> str:
        if not isinstance(payload, dict):
            return ""
        sections: list[str] = []
        for key in _DESCRIPTION_SECTIONS:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                sections.append(value.strip())
        return "\n".join(sections)
