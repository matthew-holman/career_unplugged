from __future__ import annotations

from bs4 import BeautifulSoup

from app.job_scrapers.scraper import Source


class Personio:
    source = Source.PERSONIO

    @staticmethod
    def extract_description(soup: BeautifulSoup) -> str:
        container = soup.select_one("div#job-details")
        if container is None:
            return ""

        for selector in ["form", "button", "script", "style"]:
            for tag in container.select(selector):
                tag.decompose()

        text = container.get_text(" ", strip=True)
        text = " ".join(text.split()).strip()
        if not text:
            return ""

        lowered = text.lower()
        blocked_phrases = ["apply now", "submit application", "upload cv"]
        if any(phrase in lowered for phrase in blocked_phrases):
            return ""

        return text
