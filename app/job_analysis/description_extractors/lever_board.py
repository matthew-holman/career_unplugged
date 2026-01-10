from bs4 import BeautifulSoup

from app.job_scrapers.scraper import Source


class LeverBoard:
    source = Source.LEVER

    @staticmethod
    def extract_description(soup: BeautifulSoup) -> str:
        job_description = soup.select_one("div.content")
        return job_description.decode_contents()
