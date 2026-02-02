from urllib.parse import quote

from app.job_analysis.description_extractors.linkedin import (
    extract_external_apply_url_from_linkedin_html,
)


def test_extract_external_apply_url_from_linkedin_html() -> None:
    external_url = "https://jobs.ashbyhq.com/example/123"
    encoded = quote(external_url, safe="")
    linkedin_url = (
        "https://www.linkedin.com/jobs/view/externalApply/?"
        f"url={encoded}&tracking=foo"
    )
    html = (
        "<html><body>"
        '<code id="applyUrl" style="display:none">'
        f'<!--"{linkedin_url}"-->'
        "</code>"
        "</body></html>"
    )

    assert extract_external_apply_url_from_linkedin_html(html) == external_url


def test_extract_external_apply_url_from_linkedin_html_missing() -> None:
    html = "<html><body><p>No apply URL</p></body></html>"
    assert extract_external_apply_url_from_linkedin_html(html) is None
