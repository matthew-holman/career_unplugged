from app.job_scrapers.scraper import JobResponse


class AtsScraper:
    """
    Base interface for all ATS scrapers.
    Each subclass must implement:
      - supports(url: str) -> bool
      - scrape(scraper_input: Optional[ScraperInput]) -> JobResponse
    """

    @classmethod
    def supports(cls, url: str) -> bool:
        """Return True if this scraper can handle the given URL."""
        raise NotImplementedError

    def scrape(self, url: str) -> JobResponse:
        """Perform the scrape and return a JobResponse."""
        raise NotImplementedError
