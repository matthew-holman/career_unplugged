from urllib.parse import urljoin, urlparse

import requests

from bs4 import BeautifulSoup

from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.scraper import JobPost, JobResponse, Location, Source
from app.utils.country_resolver import CountryResolver
from app.utils.log_wrapper import LoggerFactory, LogLevels

logger = LoggerFactory.get_logger("TeamTailorScraper", log_level=LogLevels.DEBUG)


class TeamTailorScraper(AtsScraper):

    @property
    def source_name(self) -> Source:
        return Source.TEAMTAILOR

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

    def scrape(self) -> JobResponse:
        jobs_url = self._resolve_jobs_index_url(self.career_page.url)
        if not jobs_url:
            logger.warning(
                f"Could not resolve Teamtailor jobs page from: {self.career_page.url}"
            )
            return JobResponse(jobs=[])

        logger.info(f"Fetching Teamtailor jobs from {jobs_url}")
        response = requests.get(
            jobs_url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        if response.status_code != 200:
            logger.warning(f"Failed to fetch {jobs_url}: {response.status_code}")
            return JobResponse(jobs=[])

        soup = BeautifulSoup(response.text, "html.parser")

        jobs_list = soup.find("ul", id="jobs_list_container")
        if not jobs_list:
            logger.warning(f"Teamtailor jobs container not found on {jobs_url}")
            return JobResponse(jobs=[])

        jobs: list[JobPost] = []
        seen_urls: set[str] = set()

        # iterate direct children only (each <li> is a job card)
        for li in jobs_list.find_all("li", recursive=False):
            link = li.find("a", href=True)
            if not link:
                continue

            job_title = link.get_text(strip=True)
            job_url = urljoin(jobs_url, link["href"])

            if job_url in seen_urls:
                continue
            seen_urls.add(job_url)

            # metadata area: <div class="mt-1 text-md"> <span>Dept</span> · <span>Location</span> · <span>Hybrid</span>
            metadata_container = li.find(
                "div", class_=lambda c: isinstance(c, str) and "mt-1" in c.split()
            )
            metadata_spans = (
                metadata_container.find_all("span") if metadata_container else []
            )

            if len(metadata_spans) < 5:
                logger.warning(
                    f"Skipping job: {job_title}, at: {self.career_page.company_name} with insufficient metadata."
                )
                continue

            department = (
                metadata_spans[0].get_text(strip=True)
                if len(metadata_spans) >= 1
                else None
            )
            location_raw = (
                metadata_spans[2].get_text(strip=True)
                if len(metadata_spans) >= 2
                else None
            )
            work_mode_raw = (
                metadata_spans[4].get_text(strip=True)
                if len(metadata_spans) >= 3
                else None
            )

            # Keep location parsing simple for now; you can improve later
            city = None
            country = None
            if location_raw:
                city = location_raw.split(",")[0].strip()

            if city and not country:
                country = CountryResolver.resolve_country(city)

            jobs.append(
                JobPost(
                    title=job_title,
                    company_name=self.career_page.company_name,
                    company_url=jobs_url,
                    location=Location(city=city, country=country),
                    date_posted=None,
                    job_url=job_url,
                    job_type=None,
                    description=None,
                    remote_status=self.parse_remote_status(work_mode_raw),
                    source=self.source_name
                )
            )

            logger.debug(
                f"Parsed Teamtailor job card: title='{job_title}', "
                f"dept='{department}', location='{location_raw}', work_mode='{work_mode_raw}', url='{job_url}'"
            )

        return JobResponse(jobs=jobs)

    @staticmethod
    def _resolve_jobs_index_url(url: str) -> str | None:
        """
        Normalize a Teamtailor URL to a job listings index page.
        Tries:
          1) If URL already includes '/jobs' -> use it
          2) base + '/jobs'
          3) Discover a jobs link from the landing page HTML
        """
        cleaned = url.strip()

        # If already on a jobs page, keep it
        if "/jobs" in urlparse(cleaned).path:
            return cleaned

        # Try base + /jobs
        base = f"{urlparse(cleaned).scheme}://{urlparse(cleaned).netloc}"
        candidate = urljoin(base + "/", "jobs")
        try:
            r = requests.get(
                candidate,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
                allow_redirects=True,
            )
            if r.status_code == 200:
                return r.url  # keep redirects (e.g. /en/jobs)
        except Exception as e:
            logger.debug(f"Error probing {candidate}: {e}")

        # Fallback: fetch landing page and look for a jobs link
        try:
            landing = requests.get(
                cleaned,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
                allow_redirects=True,
            )
            if landing.status_code != 200:
                return None

            soup = BeautifulSoup(landing.text, "html.parser")
            # prioritize likely candidates
            selectors = [
                "a[href$='/jobs']",
                "a[href*='/jobs']",
            ]
            for sel in selectors:
                a = soup.select_one(sel)
                if a and a.get("href"):
                    return urljoin(landing.url, a["href"])
        except Exception as e:
            logger.debug(f"Error discovering jobs link from {cleaned}: {e}")

        return None
