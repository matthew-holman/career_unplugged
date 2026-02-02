import re

from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup
from bs4.element import Comment

from app.models.job import Source


class LinkedIn:
    source = Source.LINKEDIN

    @staticmethod
    def extract_description(soup: BeautifulSoup) -> str:
        description_section = soup.find(
            "section", class_="core-section-container my-3 description"
        )
        if description_section:
            # keep as HTML to preserve wording, but you're regexing so either is fine
            return description_section.decode_contents()
        return ""


def extract_external_apply_url_from_linkedin_html(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    code = soup.find("code", id="applyUrl")
    if not code:
        return None

    comment = next((node for node in code.contents if isinstance(node, Comment)), None)
    if comment is None:
        return None

    match = re.search(r'"(?P<url>https?://[^"]+)"', str(comment))
    if not match:
        return None

    linkedin_url = match.group("url")
    try:
        parsed = urlparse(linkedin_url)
    except ValueError:
        return None

    params = parse_qs(parsed.query)
    external_url_values = params.get("url")
    if not external_url_values:
        return None

    external_url = unquote(external_url_values[0])
    return external_url or None
