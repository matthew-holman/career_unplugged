from bs4 import BeautifulSoup

from app.job_scrapers.scraper import Source


class AshbyBoard:
    source = Source.ASHBY

    @staticmethod
    def extract_description(soup: BeautifulSoup) -> str:
        job_description = soup.select_one("script")
        return job_description.decode_contents()
