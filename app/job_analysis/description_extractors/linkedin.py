from bs4 import BeautifulSoup

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
