from bs4 import BeautifulSoup

from app.job_scrapers.scraper import Source


class GreenHouseBoard:
    source = Source.GREENHOUSE_BOARD

    @staticmethod
    def extract_description(soup: BeautifulSoup) -> str:
        job_description = soup.select_one("main.job-post div.job-post-container")
        if job_description is None:
            return ""
        return job_description.decode_contents()
