from __future__ import annotations

import json

from bs4 import BeautifulSoup, Tag

from app.job_scrapers.scraper import Source
from app.models import Job


class Jobylon:
    """
    emp.jobylon.com job pages embed a schema.org JobPosting as JSON-LD whose
    ``description`` holds the full ad HTML.
    """

    source = Source.JOBYLON

    @staticmethod
    def extract_description(soup: BeautifulSoup, job: Job) -> str:
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            if not isinstance(script, Tag):
                continue
            raw = script.string or script.get_text()
            if not raw or not raw.strip():
                continue
            try:
                data: object = json.loads(raw)
            except json.JSONDecodeError:
                continue
            description = Jobylon.description_from_json_ld(data)
            if description:
                return description
        return ""

    @staticmethod
    def description_from_json_ld(data: object) -> str:
        candidates: list[object] = data if isinstance(data, list) else [data]
        for item in candidates:
            if not isinstance(item, dict) or item.get("@type") != "JobPosting":
                continue
            description = item.get("description")
            if isinstance(description, str) and description.strip():
                return description.strip()
        return ""
