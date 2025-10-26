import requests

from bs4 import BeautifulSoup

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import JobPost, JobResponse, Location
from app.utils.log_wrapper import LoggerFactory, LogLevels

logger = LoggerFactory.get_logger("TeamtailorScraper", log_level=LogLevels.DEBUG)


class TeamtailorScraper(AtsScraper):

    @classmethod
    def supports(cls, url: str) -> bool:
        """
        Return True if the given URL belongs to a Teamtailor-powered site.
        """
        try:
            response = requests.get(
                url,
                timeout=5,
                headers={"User-Agent": "Mozilla/5.0 (compatible; JobScraper/1.0)"},
            )
            html = response.text.lower()
        except Exception as e:
            logger.warning(f"Failed to fetch {url} for ATS detection: {e}")
            return False

        # Single simple test — matches JS, CSS, or inline data
        if "teamtailor" in html:
            logger.debug(f"Detected Teamtailor ATS on {url}")
            return True

        return False

    def scrape(self, url: str) -> JobResponse:
        logger.info(f"Fetching Teamtailor jobs from {url}")
        response = requests.get(url)
        if response.status_code != 200:
            logger.warning(f"Failed to fetch {url}: {response.status_code}")
            return JobResponse(jobs=[])

        soup = BeautifulSoup(response.text, "html.parser")
        job_links = [
            a["href"]
            for a in soup.select("a[href*='/jobs/']")
            if a["href"].startswith("http")
        ]

        jobs = []
        for job_url in job_links:
            job_title = job_url.split("/")[-1].replace("-", " ").title()
            jobs.append(
                JobPost(
                    title=job_title,
                    company_name="Unknown",
                    company_url=url,
                    location=Location(
                        city=None, country="Sweden"
                    ),  # you can improve this
                    date_posted=None,
                    job_url=job_url,
                    job_type=None,
                    description=None,
                )
            )

        return JobResponse(jobs=jobs)
