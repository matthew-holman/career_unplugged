from pathlib import Path

from bs4 import BeautifulSoup

from app.job_analysis.description_extractors.recruitee import Recruitee


def test_recruitee_description_extraction() -> None:
    html = Path("tests/fixtures/recruitee_job_detail.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    description_html = Recruitee.extract_description(soup)
    assert description_html

    text = BeautifulSoup(description_html, "html.parser").get_text(" ", strip=True)
    assert "Hostaway is the market-leading SaaS scale-up" in text
    assert "Full name" not in text
    assert "Email address" not in text
    assert "Upload" not in text
