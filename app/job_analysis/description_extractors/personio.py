from __future__ import annotations

from bs4 import BeautifulSoup

from app.job_scrapers.scraper import Source
from app.models import Job


class Personio:
    source = Source.PERSONIO

    @staticmethod
    def extract_description(soup: BeautifulSoup, job: Job) -> str:
        # Legacy markup used div#job-details; current markup splits the ad into
        # .detail-content-block sections (title + rich-text description each).
        containers = soup.select("div#job-details") or soup.select(
            ".detail-content-block"
        )
        if not containers:
            return ""

        for container in containers:
            for selector in ["form", "button", "script", "style"]:
                for tag in container.select(selector):
                    tag.decompose()

        text = " ".join(container.get_text(" ", strip=True) for container in containers)
        text = " ".join(text.split()).strip()
        if not text:
            return ""

        lowered = text.lower()
        blocked_phrases = ["apply now", "submit application", "upload cv"]
        if any(phrase in lowered for phrase in blocked_phrases):
            return ""

        return text
