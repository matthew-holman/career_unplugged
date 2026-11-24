from dataclasses import dataclass

import pytest

from bs4 import BeautifulSoup

from app.job_analysis.description_extractors.jobylon import Jobylon
from app.job_scrapers.ats_scraper_base import AtsScraper
from app.job_scrapers.ats_scrapers.ashby_board_scraper import AshbyBoardScraper
from app.job_scrapers.ats_scrapers.greenhouse_embedded_scraper import (
    GreenHouseEmbedScraper,
)
from app.job_scrapers.ats_scrapers.jobylon_scraper import (
    JobylonEmbed,
    JobylonFilterError,
    JobylonJobCard,
    JobylonScraper,
    find_jobylon_embed,
    jobylon_job_url,
)
from app.job_scrapers.ats_scrapers.teamtailor_scraper import TeamTailorScraper
from app.job_scrapers.ats_scrapers.workable_scraper import WorkableScraper
from app.job_scrapers.scraper import RemoteStatus, Source
from app.models import CareerPage, Job
from tests.test_job_scrapers.test_ats_scrapers.ats_test_base import run_ats_scraper_test

EMPTY_SOUP = BeautifulSoup("", "html.parser")


def _embed_page(config: str) -> str:
    return f"""
    <html><body>
    <div id="jobylon-jobs-widget"></div>
    <script type="text/javascript">
      /*** CONFIGURATION ***/
      {config}

      /*** SECRET CONFIGURATION ***/
      /*
        var jbl_filters = {{
            category_ids: [1],
            language_codes: ['en', 'sv']
        }};
      */
      // var jbl_group_id = 999;

      (function() {{
        var el = document.createElement('script');
        el.src = 'https://cdn.jobylon.com/embedder.js';
        d = (document.getElementsByTagName('head')[0]);
        d.appendChild(el);
      }})();
    </script>
    </body></html>
    """


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


COMPANY_PAGE = _embed_page("var jbl_company_id = \t3340;\n var jbl_version = 'v2';")
GROUP_PAGE = _embed_page(
    "var jbl_group_id = 288;\n var jbl_version = 'v2';\n"
    "var jbl_filters = {\n    layers_3_ids: [41756, 41757],\n"
    "    language_codes: ['en', 'sv'],\n    show_filters: 1\n};"
)
IFRAME_PAGE = """
<html><body>
<iframe src="https://cdn.jobylon.com/jobs/companies/2894/embed/v3/?show_filters=1"
        height="300"></iframe>
</body></html>
"""

LIST_HTML = """
<div class="job-wrapper horizontal js-job-wrapper">
  <a id="job-399205" class="js-job"
     href="https://emp.jobylon.com/jobs/399205-dollarstore-ab-butiksmedarbetare-till-skovde/?utm_source=x"
     target="_blank">
    <div class="job">
      <img src="https://media-eu.jobylon.com/logo.jpg" alt="Dollarstore AB">
      <p class="title">Butiksmedarbetare till Skövde</p>
      <p class="text-muted job-details">
        <small>
          <strong>Dollarstore AB</strong>
          | Skövde
        </small>
      </p>
    </div>
  </a>
  <a id="job-398975" class="js-job"
     href="https://emp.jobylon.com/jobs/398975-tokmanni-relex-super-user/">
    <div class="job">
      <p class="title">Relex Super User (Remote)</p>
      <p class="text-muted job-details">
        <small><strong>Tokmanni</strong> | Stockholm +1 mere</small>
      </p>
    </div>
  </a>
  <a id="job-1" class="js-job" href="https://emp.jobylon.com/jobs/1-no-location/">
    <div class="job"><p class="title">No Location</p>
      <p class="job-details"><small><strong>Acme</strong></small></p></div>
  </a>
  <a id="job-2" class="js-job" href="https://example.com/jobs/2-elsewhere/">
    <div class="job"><p class="title">Off-site link</p></div>
  </a>
  <a id="job-3" class="js-job" href="https://emp.jobylon.com/jobs/3-untitled/">
    <div class="job"><p class="title"> </p></div>
  </a>
</div>
"""


def _scraper(url: str = "https://careers.acme.se") -> JobylonScraper:
    return JobylonScraper(CareerPage(company_name="acme", url=url))


# --- supports() --------------------------------------------------------------


@pytest.mark.parametrize("html", [COMPANY_PAGE, GROUP_PAGE, IFRAME_PAGE])
def test_supports_jobylon_embeds(html: str) -> None:
    assert JobylonScraper.supports(url="https://careers.acme.se", soup=_soup(html))


@pytest.mark.parametrize(
    "html",
    [
        "",
        # Config only in comments.
        _embed_page("// var jbl_company_id = 1;"),
        # Config without the Jobylon embedder.
        "<script>var jbl_company_id = 12;</script>",
        # External script, never parsed.
        '<script src="https://cdn.jobylon.com/embedder.js"></script>',
        # Non-Jobylon iframe / Jobylon non-jobs iframe.
        '<iframe src="https://boards.greenhouse.io/embed/job_board?for=acme"></iframe>',
        '<iframe src="https://cdn.jobylon.com/applications/application-form/1/embed/"></iframe>',
        # Ambiguous: two different job iframes and no config.
        '<iframe src="https://cdn.jobylon.com/jobs/companies/1/embed/v3/"></iframe>'
        '<iframe src="https://cdn.jobylon.com/jobs/companies/2/embed/v3/"></iframe>',
    ],
)
def test_does_not_support_other_pages(html: str) -> None:
    assert not JobylonScraper.supports(url="https://careers.acme.se", soup=_soup(html))


def test_does_not_support_other_ats_urls() -> None:
    for url in (
        "https://jobs.ashbyhq.com/acme",
        "https://acme.teamtailor.com/",
        "https://apply.workable.com/acme/",
    ):
        assert not JobylonScraper.supports(url=url, soup=EMPTY_SOUP)


def test_other_scrapers_do_not_claim_jobylon_pages() -> None:
    url = "https://careers.acme.se"
    for html in (COMPANY_PAGE, GROUP_PAGE, IFRAME_PAGE):
        for scraper_cls in (
            WorkableScraper,
            AshbyBoardScraper,
            GreenHouseEmbedScraper,
            TeamTailorScraper,
        ):
            assert not scraper_cls.supports(url=url, soup=_soup(html))


# --- embed discovery -----------------------------------------------------------


def test_find_embed_company_config_ignores_comments() -> None:
    embed = find_jobylon_embed(_soup(COMPANY_PAGE))
    assert embed == JobylonEmbed(embed_type="companies", embed_id="3340")
    assert embed.list_url() == "https://cdn.jobylon.com/jobs/companies/3340/embed/v5/"


def test_find_embed_group_config_with_filters() -> None:
    embed = find_jobylon_embed(_soup(GROUP_PAGE))
    assert embed is not None
    assert embed.embed_type == "company-groups"
    assert embed.embed_id == "288"
    assert embed.params == (
        ("layers_3_ids", "41756,41757"),
        ("language_codes", "en,sv"),
        ("show_filters", "1"),
    )
    assert embed.list_url() == (
        "https://cdn.jobylon.com/jobs/company-groups/288/embed/v5/"
        "?layers_3_ids=41756%2C41757&language_codes=en%2Csv&show_filters=1"
    )


def test_find_embed_empty_filters() -> None:
    page = _embed_page("var jbl_company_id = 6;\nvar jbl_filters = {\n};")
    embed = find_jobylon_embed(_soup(page))
    assert embed == JobylonEmbed(embed_type="companies", embed_id="6")


def test_find_embed_config_wins_over_iframes() -> None:
    page = COMPANY_PAGE + (
        '<iframe src="https://cdn.jobylon.com/jobs/companies/2432/embed/v3/"></iframe>'
    )
    embed = find_jobylon_embed(_soup(page))
    assert embed is not None
    assert embed.embed_id == "3340"


def test_find_embed_iframe_keeps_query_params() -> None:
    embed = find_jobylon_embed(_soup(IFRAME_PAGE))
    assert embed == JobylonEmbed(
        embed_type="companies", embed_id="2894", params=(("show_filters", "1"),)
    )


def test_find_embed_conflicting_configs_is_ambiguous() -> None:
    page = _embed_page("var jbl_company_id = 1;\nvar jbl_group_id = 2;")
    assert find_jobylon_embed(_soup(page)) is None


def test_unparseable_filters_raise_and_skip_board(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = _embed_page("var jbl_company_id = 1;\nvar jbl_filters = { a: someVar };")
    soup = _soup(page)
    with pytest.raises(JobylonFilterError):
        find_jobylon_embed(soup)

    def fail_fetch(url: str, **kwargs: object) -> None:
        raise AssertionError("should not fetch")

    monkeypatch.setattr(AtsScraper, "_fetch_page", staticmethod(fail_fetch))
    assert JobylonScraper.supports(url="https://careers.acme.se", soup=soup)
    assert _scraper().find_job_cards(soup) == []


# --- list parsing ------------------------------------------------------------


def test_jobylon_job_url() -> None:
    assert (
        jobylon_job_url("https://emp.jobylon.com/jobs/1-a/?utm=x#y")
        == "https://emp.jobylon.com/jobs/1-a/"
    )
    assert jobylon_job_url("/jobs/1-a/") == "https://emp.jobylon.com/jobs/1-a/"
    assert jobylon_job_url("https://emp.jobylon.com/companies/1/") is None
    assert jobylon_job_url("https://example.com/jobs/1-a/") is None


def test_parse_list_html() -> None:
    cards = JobylonScraper.parse_list_html(LIST_HTML)

    assert cards == [
        JobylonJobCard(
            title="Butiksmedarbetare till Skövde",
            job_url="https://emp.jobylon.com/jobs/399205-dollarstore-ab-butiksmedarbetare-till-skovde/",
            location="Skövde",
        ),
        JobylonJobCard(
            title="Relex Super User (Remote)",
            job_url="https://emp.jobylon.com/jobs/398975-tokmanni-relex-super-user/",
            location="Stockholm",
        ),
        JobylonJobCard(
            title="No Location",
            job_url="https://emp.jobylon.com/jobs/1-no-location/",
            location=None,
        ),
    ]


def test_parse_job_card() -> None:
    cards = JobylonScraper.parse_list_html(LIST_HTML)
    job = _scraper().parse_job_card(cards[1])

    assert job is not None
    assert job.title == "Relex Super User (Remote)"
    assert job.job_url == cards[1].job_url
    assert job.company_name == "acme"
    assert job.company_url == "https://careers.acme.se"
    assert job.source == Source.JOBYLON
    assert job.remote_status == RemoteStatus.REMOTE
    assert job.location is not None
    assert job.location.city == "Stockholm"


def test_parse_job_card_rejects_non_card() -> None:
    assert _scraper().parse_job_card({"title": "x"}) is None


# --- fetching ----------------------------------------------------------------


@dataclass(frozen=True)
class _FakeResponse:
    status_code: int
    text: str = ""


def test_find_job_cards_calls_list_embed(monkeypatch: pytest.MonkeyPatch) -> None:
    requested: list[str] = []

    def fake_fetch(url: str, **kwargs: object) -> _FakeResponse:
        requested.append(url)
        return _FakeResponse(200, LIST_HTML)

    monkeypatch.setattr(AtsScraper, "_fetch_page", staticmethod(fake_fetch))

    cards = _scraper().find_job_cards(_soup(COMPANY_PAGE))

    assert requested == ["https://cdn.jobylon.com/jobs/companies/3340/embed/v5/"]
    assert len(cards) == 3


@pytest.mark.parametrize("status_code", [404, 429, 500])
def test_find_job_cards_handles_error_status(
    monkeypatch: pytest.MonkeyPatch, status_code: int
) -> None:
    monkeypatch.setattr(
        AtsScraper,
        "_fetch_page",
        staticmethod(lambda url, **kwargs: _FakeResponse(status_code)),
    )
    assert _scraper().find_job_cards(_soup(COMPANY_PAGE)) == []


def test_find_job_cards_without_embed() -> None:
    assert _scraper().find_job_cards(EMPTY_SOUP) == []


# --- description -------------------------------------------------------------


def test_description_from_json_ld() -> None:
    html = """
    <script type="application/ld+json">{"@type": "Organization", "name": "x"}</script>
    <script type="application/ld+json">not json</script>
    <script type="application/ld+json">
      {"@context": "http://schema.org", "@type": "JobPosting",
       "title": "Engineer", "description": "<p>Build things</p>"}
    </script>
    """
    job = Job(title="Engineer", company="acme", source=Source.JOBYLON)
    assert Jobylon.extract_description(_soup(html), job) == "<p>Build things</p>"
    assert Jobylon.extract_description(EMPTY_SOUP, job) == ""
    assert Jobylon.description_from_json_ld([{"@type": "JobPosting"}]) == ""


@pytest.mark.integration
@pytest.mark.network
def test_jobylon_scraper() -> None:
    career_page = CareerPage(
        company_name="koenigsegg",
        url="https://koenigsegg.jobylon.com",
    )

    run_ats_scraper_test(
        scraper_cls=JobylonScraper,
        career_page=career_page,
    )
