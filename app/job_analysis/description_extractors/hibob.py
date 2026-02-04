from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.job_analysis.description_extractor import DescriptionExtractor
from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import Source
from app.log import Log


class HiBob(DescriptionExtractor):
    source = Source.HIBOB

    @staticmethod
    def extract_description(soup: BeautifulSoup) -> str:
        job_url = HiBob._extract_job_url(soup)
        if not job_url:
            Log.warning("HiBob description extractor: job URL not found in HTML")
            return ""

        job_id = HiBob._extract_job_id(job_url)
        if not job_id:
            Log.warning(
                "HiBob description extractor: job ID not found for " f"{job_url}"
            )
            return ""

        api_url = HiBob._build_application_form_url(job_url, job_id)
        if not api_url:
            return ""

        company_identifier = HiBob._extract_company_identifier(job_url)
        if not company_identifier:
            Log.warning(
                "HiBob description extractor: company identifier not found for "
                f"{job_url}"
            )
            return ""

        response = AtsScraper._fetch_page(
            api_url, headers={"companyidentifier": company_identifier}
        )
        if not response:
            return ""

        try:
            payload = response.json()
        except ValueError:
            Log.warning(
                "HiBob description extractor: failed to decode JSON from " f"{api_url}"
            )
            return ""

        description = HiBob._extract_description_from_payload(payload)
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
    def _extract_job_id(job_url: str) -> str | None:
        parsed = urlparse(job_url)
        path = (parsed.path or "").strip("/")
        if not path:
            return None

        if "/job-ad/" in path:
            return path.split("/job-ad/", 1)[1].split("/", 1)[0]

        parts = path.split("/")
        return parts[-1] if parts else None

    @staticmethod
    def _build_application_form_url(job_url: str, job_id: str) -> str | None:
        parsed = urlparse(job_url)
        if not parsed.scheme or not parsed.netloc:
            return None
        base = f"{parsed.scheme}://{parsed.netloc}"
        return f"{base}/api/job-ad/{job_id}/application-form"

    @staticmethod
    def _extract_company_identifier(job_url: str) -> str | None:
        hostname = urlparse(job_url).hostname or ""
        if not hostname.endswith("careers.hibob.com"):
            return None
        slug = hostname.split(".", 1)[0].strip()
        return slug or None

    @staticmethod
    def _extract_description_from_payload(payload: object) -> str | None:
        if not isinstance(payload, dict):
            return None

        for key in ("description", "jobAdDescription", "jobDescription"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        job_ad = payload.get("jobAd")
        if isinstance(job_ad, dict):
            value = job_ad.get("description")
            if isinstance(value, str) and value.strip():
                return value.strip()

        return None
