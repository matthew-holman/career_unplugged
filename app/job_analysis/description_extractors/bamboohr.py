from __future__ import annotations

from bs4 import BeautifulSoup

from app.job_analysis.description_extractor import DescriptionExtractor
from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import Source
from app.log import Log
from app.models import Job


class BambooHr(DescriptionExtractor):
    source = Source.BAMBOO

    @staticmethod
    def extract_description(soup: BeautifulSoup, job: Job) -> str:
        detail_url = (job.ats_source_url or "").rstrip("/") + "/detail"
        response = AtsScraper._fetch_page(detail_url)
        if not response:
            return ""

        try:
            payload = response.json()
        except ValueError:
            Log.warning(
                "BambooHR description extractor: failed to decode JSON from "
                f"{detail_url}"
            )
            return ""

        description = BambooHr._extract_description_from_payload(payload)
        return description or ""

    @staticmethod
    def _extract_job_url(soup: BeautifulSoup) -> str | None:
        canonical = soup.select_one("link[rel='canonical'][href]")
        if canonical and canonical.get("href"):
            return canonical.get("href")

        og_url = soup.select_one("meta[property='og:url'][content]")
        if og_url and og_url.get("content"):
            return og_url.get("content")

        return None

    @staticmethod
    def _extract_description_from_payload(payload: object) -> str | None:
        if not isinstance(payload, dict):
            return None
        result = payload.get("result")
        if not isinstance(result, dict):
            return None
        job_opening = result.get("jobOpening")
        if not isinstance(job_opening, dict):
            return None
        description = job_opening.get("description")
        if isinstance(description, str) and description.strip():
            return description
        return None
