from __future__ import annotations

import re

from urllib.parse import urlparse

from bs4 import BeautifulSoup, NavigableString, Tag

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.ats_scrapers.recruitee_scraper import recruitee_board_host
from app.job_scrapers.scraper import Source
from app.log import Log
from app.models import Job

_DESCRIPTION_SECTIONS = ("description", "requirements")


class Recruitee:
    """
    Prefers the offer API, GET https://{slug}.recruitee.com/api/offers/{offer},
    because custom-layout boards don't use the standard "Job description"
    headings. Falls back to parsing the job page.
    """

    source = Source.RECRUITEE

    @staticmethod
    def extract_description(soup: BeautifulSoup, job: Job) -> str:
        api_url = Recruitee.build_api_url(job.ats_source_url or "")
        if api_url:
            description = Recruitee._fetch_api_description(api_url)
            if description:
                return description
        return Recruitee._extract_page_description(soup)

    @staticmethod
    def build_api_url(job_url: str) -> str | None:
        host = recruitee_board_host(job_url)
        if not host:
            return None
        parts = [segment for segment in urlparse(job_url).path.split("/") if segment]
        # Expected path: /o/{offer_slug}
        if len(parts) < 2 or parts[0] != "o":
            return None
        return f"https://{host}/api/offers/{parts[1]}"

    @staticmethod
    def _fetch_api_description(api_url: str) -> str:
        response = AtsScraper._fetch_page(api_url)
        if not response:
            return ""
        try:
            payload: object = response.json()
        except ValueError:
            Log.warning(f"Recruitee description extractor: invalid JSON from {api_url}")
            return ""
        return Recruitee.description_from_payload(payload)

    @staticmethod
    def description_from_payload(payload: object) -> str:
        if not isinstance(payload, dict):
            return ""
        offer = payload.get("offer")
        if not isinstance(offer, dict):
            return ""
        sections: list[str] = []
        for key in _DESCRIPTION_SECTIONS:
            value = offer.get(key)
            if isinstance(value, str) and value.strip():
                sections.append(value.strip())
        return "\n".join(sections)

    @staticmethod
    def _extract_page_description(soup: BeautifulSoup) -> str:
        heading = Recruitee._find_heading(soup)
        if heading is None:
            return ""

        nodes = Recruitee._collect_description_nodes(heading)
        if not nodes:
            return ""

        html = "".join(str(node) for node in nodes)
        return html

    @staticmethod
    def _normalize_heading_text(value: str) -> str:
        return re.sub(r"\s+", " ", value.strip()).lower()

    @staticmethod
    def _find_heading(soup: BeautifulSoup) -> Tag | None:
        for heading in soup.find_all(["h2", "h3"]):
            text = heading.get_text(" ", strip=True)
            if not text:
                continue
            if Recruitee._normalize_heading_text(text) == "job description":
                return heading

        for heading in soup.find_all(["h2", "h3"]):
            text = heading.get_text(" ", strip=True)
            if not text:
                continue
            if "description" in Recruitee._normalize_heading_text(text):
                return heading

        return None

    @staticmethod
    def _collect_description_nodes(heading: Tag) -> list[Tag | NavigableString]:
        nodes: list[Tag | NavigableString] = []
        base_level = (
            int(heading.name[1]) if heading.name and heading.name[1:].isdigit() else 2
        )

        for sibling in heading.next_siblings:
            if isinstance(sibling, Tag) and sibling.name in {"h2", "h3"}:
                normalized = Recruitee._normalize_heading_text(
                    sibling.get_text(" ", strip=True)
                )
                if sibling.name == "h2" or normalized == "job requirements":
                    break
                level = int(sibling.name[1]) if sibling.name[1:].isdigit() else 2
                if level <= base_level:
                    break

            if isinstance(sibling, (Tag, NavigableString)):
                text = str(sibling).strip()
                if text:
                    nodes.append(sibling)

        return nodes
