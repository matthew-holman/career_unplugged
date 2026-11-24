from pathlib import Path

from bs4 import BeautifulSoup

from app.job_analysis.description_extractors.recruitee import Recruitee
from app.job_scrapers.scraper import Source
from app.models import Job


def test_recruitee_description_extraction() -> None:
    html = Path("tests/fixtures/recruitee_job_detail.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    job = Job(title="Engineer", company="hostaway", source=Source.RECRUITEE)
    description_html = Recruitee.extract_description(soup, job)
    assert description_html

    text = BeautifulSoup(description_html, "html.parser").get_text(" ", strip=True)
    assert "Hostaway is the market-leading SaaS scale-up" in text
    assert "Full name" not in text
    assert "Email address" not in text
    assert "Upload" not in text
