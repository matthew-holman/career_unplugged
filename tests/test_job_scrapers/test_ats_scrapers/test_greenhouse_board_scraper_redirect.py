from app.job_scrapers.ats_scraper_factory import AtsScraperFactory
from app.job_scrapers.ats_scrapers.greenhouse_board_scraper import (
    GreenHouseBoardScraper,
)
from app.models import CareerPage


def test_greenhouse_board_slug_extraction() -> None:
    assert (
        GreenHouseBoardScraper._extract_slug_from_board_url(
            "https://job-boards.greenhouse.io/taboola"
        )
        == "taboola"
    )
    assert (
        GreenHouseBoardScraper._extract_slug_from_board_url(
            "https://job-boards.greenhouse.io/taboola/"
        )
        == "taboola"
    )
    assert (
        GreenHouseBoardScraper._extract_slug_from_board_url(
            "https://job-boards.greenhouse.io/taboola/jobs/123"
        )
        == "taboola"
    )
    assert (
        GreenHouseBoardScraper._extract_slug_from_board_url(
            "https://job-boards.eu.greenhouse.io/taboola/jobs/123"
        )
        == "taboola"
    )
    assert (
        GreenHouseBoardScraper._extract_slug_from_board_url(
            "https://example.com/taboola"
        )
        is None
    )
    assert (
        GreenHouseBoardScraper._extract_slug_from_board_url(
            "https://job-boards.greenhouse.io/"
        )
        is None
    )


def test_greenhouse_board_embed_url_generation() -> None:
    assert (
        GreenHouseBoardScraper._build_embed_url(
            "job-boards.greenhouse.io",
            "taboola",
        )
        == "https://job-boards.greenhouse.io/embed/job_board?for=taboola"
    )
    assert (
        GreenHouseBoardScraper._build_embed_url(
            "job-boards.eu.greenhouse.io",
            "taboola",
        )
        == "https://job-boards.eu.greenhouse.io/embed/job_board?for=taboola"
    )


def test_greenhouse_board_redirect_fallback(requests_mock) -> None:
    board_url = "https://job-boards.greenhouse.io/taboola"
    redirect_url = "https://www.taboola.com/careers"
    embed_url = "https://job-boards.greenhouse.io/embed/job_board?for=taboola"

    embed_html = """
    <html>
      <body>
        <div class="job-posts">
          <table>
            <tr class="job-post">
              <td>
                <a href="https://boards.greenhouse.io/taboola/jobs/123">
                  <p class="body--medium">Senior Engineer</p>
                  <p class="body__secondary body--metadata">London, UK</p>
                </a>
              </td>
            </tr>
          </table>
        </div>
      </body>
    </html>
    """

    requests_mock.get(board_url, status_code=301, headers={"Location": redirect_url})
    requests_mock.get(redirect_url, text="<html>company</html>", status_code=200)
    requests_mock.get(embed_url, text=embed_html, status_code=200)

    career_page = CareerPage(
        company_name="Taboola",
        url=board_url,
        active=True,
    )

    scraper = AtsScraperFactory.get_ats_scraper(career_page)
    assert isinstance(scraper, GreenHouseBoardScraper)

    response = scraper.scrape()
    assert response.jobs
    assert response.jobs[0].title == "Senior Engineer"
    assert response.jobs[0].job_url == ("https://boards.greenhouse.io/taboola/jobs/123")
