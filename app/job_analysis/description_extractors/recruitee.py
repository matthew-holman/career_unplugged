from __future__ import annotations

import re

from bs4 import BeautifulSoup, NavigableString, Tag

from app.job_scrapers.scraper import Source


class Recruitee:
    source = Source.RECRUITEE

    @staticmethod
    def extract_description(soup: BeautifulSoup) -> str:
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
