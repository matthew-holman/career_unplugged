from __future__ import annotations

import random
import time

from datetime import datetime
from threading import Lock
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.job_scrapers.scraper import (
    DescriptionFormat,
    JobPost,
    JobResponse,
    JobType,
    Location,
    Scraper,
    ScraperInput,
    Source,
)
from app.job_scrapers.utils import (
    create_session,
    extract_emails_from_text,
    get_enum_from_job_type,
    markdown_converter,
)
from app.log import Log


class LinkedInScraper(Scraper):
    base_url = "https://www.linkedin.com"
    delay = 3
    band_delay = 4
    jobs_per_page = 25
    scraper_input: ScraperInput | None = None

    def __init__(self, proxy: str | None = None):
        """
        Initializes LinkedInScraper with the LinkedIn job search url
        """
        super().__init__(proxy=proxy)
        self.country = "EMEA"

    @property
    def source_name(self) -> Source:
        return Source.LINKEDIN

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        """
        Scrapes LinkedIn for jobs with scraper_input criteria
        :param scraper_input:
        :return: job_response
        """
        self.scraper_input = scraper_input
        job_list: list[JobPost] = []
        seen_urls = set()
        url_lock = Lock()
        page = scraper_input.offset // 25 + 25 if scraper_input.offset else 0
        seconds_old = (
            scraper_input.hours_old * 3600 if scraper_input.hours_old else None
        )
        while self._should_continue(page, job_list, scraper_input):
            Log.info(f"LinkedIn search page: {page // 25 + 1}")
            response = self._fetch_search_results(
                scraper_input,
                page,
                seconds_old,
            )
            if response is None:
                return JobResponse(jobs=job_list)

            soup = BeautifulSoup(response.text, "html.parser")
            job_cards = soup.find_all("div", class_="base-search-card")
            if len(job_cards) == 0:
                return JobResponse(jobs=job_list)

            for job_card in job_cards:
                job_url = self._extract_job_url(job_card)
                if not job_url:
                    continue

                with url_lock:
                    if job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                fetch_desc = scraper_input.linkedin_fetch_description
                job_post = self._process_job(job_card, job_url, fetch_desc)
                if job_post:
                    job_post.remote_status = scraper_input.remote_status
                    job_list.append(job_post)
                if not self._should_continue(page, job_list, scraper_input):
                    break

            if self._should_continue(page, job_list, scraper_input):
                time.sleep(random.uniform(self.delay, self.delay + self.band_delay))
                page += self.jobs_per_page

        job_list = job_list[: scraper_input.results_wanted]
        return JobResponse(jobs=job_list)

    def _process_job(
        self, job_card: Tag, job_url: str, full_descr: bool
    ) -> JobPost | None:
        title_tag = job_card.find("span", class_="sr-only")
        title = title_tag.get_text(strip=True) if title_tag else "N/A"

        company_tag = job_card.find("h4", class_="base-search-card__subtitle")
        company_a_tag = company_tag.find("a") if company_tag else None
        company_url = (
            urlunparse(urlparse(company_a_tag.get("href"))._replace(query=""))
            if company_a_tag and company_a_tag.has_attr("href")
            else ""
        )
        company = company_a_tag.get_text(strip=True) if company_a_tag else "N/A"

        metadata_card = job_card.find("div", class_="base-search-card__metadata")
        location = self._get_location(metadata_card)

        datetime_tag = (
            metadata_card.find(
                "time",
                class_=[
                    "job-search-card__listdate",
                    "job-search-card__listdate--new",
                ],
            )
            if metadata_card
            else None
        )
        listing_date = description = job_type = None
        if datetime_tag and "datetime" in datetime_tag.attrs:
            datetime_str = datetime_tag["datetime"]
            try:
                listing_date = datetime.strptime(datetime_str, "%Y-%m-%d").date()
            except Exception:
                listing_date = None
        if full_descr:
            description, job_type = self._get_job_description(job_url)

        return JobPost(
            title=title,
            company_name=company,
            company_url=company_url,
            location=location,
            date_posted=listing_date,
            job_url=job_url,
            job_type=job_type,
            description=description,
            emails=extract_emails_from_text(description) if description else None,
            listing_date=listing_date,
            source=self.source_name,
        )

    def _get_job_description(
        self, job_page_url: str
    ) -> tuple[str | None, list[JobType] | None]:
        """
        Retrieves job description by going to the job page url
        :param job_page_url:
        :return: description or None
        """
        assert self.scraper_input is not None
        try:
            session = create_session(is_tls=False, has_retry=True, delay=15)
            response = session.get(
                job_page_url,
                headers=self.headers,
                timeout=5,
                proxies=self.proxy,
            )
            response.raise_for_status()
        except Exception:
            return None, None
        if response.url == "https://www.linkedin.com/signup":
            return None, None

        soup = BeautifulSoup(response.text, "html.parser")
        div_content = soup.find(
            "div", class_=lambda x: x and "show-more-less-html__markup" in x
        )
        description = None
        if div_content is not None:

            def remove_attributes(tag):
                for attr in list(tag.attrs):
                    del tag[attr]
                return tag

            div_content = remove_attributes(div_content)
            description = div_content.prettify(formatter="html")
            if self.scraper_input.description_format == DescriptionFormat.MARKDOWN:
                description = markdown_converter(description)
        return description, self._parse_job_type(soup)

    def _get_location(self, metadata_card: Tag | None) -> Location:
        """
        Extracts the location data from the job metadata card.
        :param metadata_card
        :return: location
        """
        location = Location()
        if metadata_card is not None:
            location_tag = metadata_card.find(
                "span", class_="job-search-card__location"
            )
            location_string = location_tag.text.strip() if location_tag else "N/A"
            parts = location_string.split(", ")
            if len(parts) == 1:
                country = parts[0]
                location = Location(country=country)
            if len(parts) == 2:
                city, country = parts
                location = Location(
                    city=city,
                    country=country,
                )
            elif len(parts) == 3:
                city, state, country = parts
                location = Location(city=city, state=state, country=country)
        return location

    @staticmethod
    def _parse_job_type(soup_job_type: BeautifulSoup) -> list[JobType] | None:
        """
        Gets the job type from job page
        :param soup_job_type:
        :return: JobType
        """
        h3_tag = soup_job_type.find(
            "h3",
            class_="description__job-criteria-subheader",
            string=lambda text: "Employment type" in text,
        )
        employment_type = None
        if h3_tag:
            employment_type_span = h3_tag.find_next_sibling(
                "span",
                class_="description__job-criteria-text description__job-criteria-text--criteria",  # noqa
            )
            if employment_type_span:
                employment_type = employment_type_span.get_text(strip=True)
                employment_type = employment_type.lower()
                employment_type = employment_type.replace("-", "")

        job_type = get_enum_from_job_type(employment_type) if employment_type else None
        return [job_type] if job_type else []

    @staticmethod
    def _should_continue(
        page: int, job_list: list[JobPost], scraper_input: ScraperInput
    ) -> bool:
        return len(job_list) < scraper_input.results_wanted and page < 1000

    def _fetch_search_results(
        self,
        scraper_input: ScraperInput,
        page: int,
        seconds_old: int | None,
    ):
        session = create_session(is_tls=False, has_retry=True, delay=15)
        params = {
            "keywords": scraper_input.search_term,
            "location": scraper_input.location,
            "distance": scraper_input.distance,
            "f_WT": (
                scraper_input.remote_status.value
                if scraper_input.remote_status
                else None
            ),
            "f_JT": (
                self.job_type_code(scraper_input.job_type)
                if scraper_input.job_type
                else None
            ),
            "pageNum": 0,
            "start": page + scraper_input.offset,
            "f_AL": "true" if scraper_input.easy_apply else None,
            "f_C": (
                ",".join(map(str, scraper_input.linkedin_company_ids))
                if scraper_input.linkedin_company_ids
                else None
            ),
        }
        if seconds_old is not None:
            params["f_TPR"] = f"r{seconds_old}"

        params = {k: v for k, v in params.items() if v is not None}
        try:
            response = session.get(
                f"{self.base_url}/jobs-guest/jobs/api/seeMoreJobPostings/search?",  # noqa
                params=params,
                allow_redirects=True,
                proxies=self.proxy,
                headers=self.headers,
                timeout=10,
            )
            if response.status_code not in range(200, 400):
                if response.status_code == 429:
                    err = "429 Response - " "Blocked by LinkedIn for too many requests"
                else:
                    err = f"LinkedIn response status code {response.status_code}"
                    err += f" - {response.text}"
                Log.error(err)
                return None
            return response
        except Exception as e:
            if "Proxy responded with" in str(e):
                Log.error("LinkedIn: Bad proxy")
            else:
                Log.error(f"LinkedIn: {str(e)}")
            return None

    def _extract_job_url(self, job_card: Tag) -> str | None:
        href_tag = job_card.find("a", class_="base-card__full-link")
        if not href_tag or "href" not in href_tag.attrs:
            return None
        href = href_tag.attrs["href"].split("?")[0]
        job_id = href.split("-")[-1]
        return f"{self.base_url}/jobs/view/{job_id}"

    @staticmethod
    def job_type_code(job_type_enum: JobType) -> str:
        return {
            JobType.FULL_TIME: "F",
            JobType.PART_TIME: "P",
            JobType.INTERNSHIP: "I",
            JobType.CONTRACT: "C",
            JobType.TEMPORARY: "T",
        }.get(job_type_enum, "")

    headers = {
        "authority": "www.linkedin.com",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",  # noqa
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "max-age=0",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",  # noqa
    }
