import json

from typing import Optional

from bs4 import BeautifulSoup

from app.job_scrapers.scraper import Source


class Teamtailor:
    source = Source.TEAMTAILOR

    @staticmethod
    def extract_description(soup: BeautifulSoup) -> str:
        """
        Teamtailor description extractor.

        1) Preferred: <section class="company-links ..."> containing <div class="prose ..."> (returns HTML).
        2) Fallback: <script type="application/ld+json"> (returns best-effort text/HTML-ish string).
        """
        prose_div = Teamtailor._extract_prose(soup)
        if prose_div:
            return prose_div

        script_description = Teamtailor._extract_script_description(soup)
        if script_description:
            return script_description

        return ""

    @staticmethod
    def _extract_prose(soup: BeautifulSoup) -> str:
        # 1) Primary: section.company-links -> div.prose
        prose_div = soup.select_one("section.company-links div.prose")
        return prose_div.decode_contents()

    @staticmethod
    def _extract_script_description(soup: BeautifulSoup) -> Optional[str]:  # noqa: C901
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = script.string or script.get_text(strip=False)
            if not raw or not raw.strip():
                continue

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            # JSON-LD can be a dict, list, or have @graph
            candidates = []
            if isinstance(data, dict):
                candidates.append(data)
                graph = data.get("@graph")
                if isinstance(graph, list):
                    candidates.extend([x for x in graph if isinstance(x, dict)])
            elif isinstance(data, list):
                candidates.extend([x for x in data if isinstance(x, dict)])

            for item in candidates:
                item_type = item.get("@type") or item.get("type")
                if item_type == "JobPosting" or (
                    isinstance(item_type, list) and "JobPosting" in item_type
                ):
                    description = item.get("description")
                    if isinstance(description, str) and description.strip():
                        return description
        return None
