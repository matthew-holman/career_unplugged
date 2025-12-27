from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import Source, JobResponse
from app.log import Log


class GreenHouseScraper(AtsScraper):

    @property
    def source_name(self) -> Source:
        return Source.GREENHOUSE

    @classmethod
    def supports(cls, url: str) -> bool:
        """
        Return True if the given URL belongs to a Greenhouse-jobs list.
        """
        try:
            response = GreenHouseScraper._fetch_page(url)
            html = response.text.lower()
        except Exception as e:
            Log.warning(f"Failed to fetch {url} for ATS detection: {e}")
            return False

        if "greenhouse-job-board" in html:
            Log.debug(f"Detected Green House jobs list")
            return True

        return False

    def scrape(self) -> JobResponse:
        Log.warning(f"Green House scraper is not implemented yet.")
        return JobResponse(jobs=[])

