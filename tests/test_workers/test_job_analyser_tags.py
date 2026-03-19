"""Tests for tag extraction in the job analyser."""

from unittest.mock import patch

from app.models.job import Job
from app.models.job_tag import TagCategory
from app.workers.job_analyser import _extract_tags

TECH = {
    "Python": r"\bPython\b",
    "FastAPI": r"\bFastAPI\b",
    "Docker": r"\bDocker\b",
    "Kubernetes": r"\b(Kubernetes|K8s)\b",
}

ROLE = {
    "Engineering Manager": r"\bengineering\s+manager\b",
    "Tech Lead": r"\b(tech(nical)?\s+lead|team\s+lead)\b",
}


def _make_job(title: str, job_id: int = 1) -> Job:
    return Job(
        id=job_id,
        title=title,
        company="Acme",
        ats_source_url=f"https://example.com/job/{job_id}",
    )


def test_tech_stack_tag_detected_in_description():
    job = _make_job("Engineering Manager")
    description = "We use Python and FastAPI for our backend services."

    with patch("app.workers.job_analyser.TECH_STACK_TAGS", TECH), patch(
        "app.workers.job_analyser.ROLE_TYPE_TAGS", ROLE
    ):
        tags = _extract_tags(job, description)

    names = {t.name for t in tags}
    assert "Python" in names
    assert "FastAPI" in names
    assert all(
        t.category == TagCategory.TECH_STACK
        for t in tags
        if t.name in {"Python", "FastAPI"}
    )


def test_role_type_tag_detected_in_job_title():
    job = _make_job("Senior Engineering Manager")
    description = "You will lead a team of engineers."

    with patch("app.workers.job_analyser.TECH_STACK_TAGS", TECH), patch(
        "app.workers.job_analyser.ROLE_TYPE_TAGS", ROLE
    ):
        tags = _extract_tags(job, description)

    role_tags = {t.name for t in tags if t.category == TagCategory.ROLE_TYPE}
    assert "Engineering Manager" in role_tags


def test_role_type_tag_detected_in_description():
    job = _make_job("Team Lead")
    description = "You will act as a team lead for the platform squad."

    with patch("app.workers.job_analyser.TECH_STACK_TAGS", TECH), patch(
        "app.workers.job_analyser.ROLE_TYPE_TAGS", ROLE
    ):
        tags = _extract_tags(job, description)

    role_tags = {t.name for t in tags if t.category == TagCategory.ROLE_TYPE}
    assert "Tech Lead" in role_tags


def test_no_match_returns_empty_list():
    job = _make_job("Accountant")
    description = "Manage quarterly financial reports and budgets."

    with patch("app.workers.job_analyser.TECH_STACK_TAGS", TECH), patch(
        "app.workers.job_analyser.ROLE_TYPE_TAGS", ROLE
    ):
        tags = _extract_tags(job, description)

    assert tags == []


def test_multiple_categories_detected_independently():
    job = _make_job("Engineering Manager")
    description = (
        "Stack: Python, Docker, Kubernetes. You will manage a team of 5 engineers."
    )

    with patch("app.workers.job_analyser.TECH_STACK_TAGS", TECH), patch(
        "app.workers.job_analyser.ROLE_TYPE_TAGS", ROLE
    ):
        tags = _extract_tags(job, description)

    tech_names = {t.name for t in tags if t.category == TagCategory.TECH_STACK}
    role_names = {t.name for t in tags if t.category == TagCategory.ROLE_TYPE}

    assert "Python" in tech_names
    assert "Docker" in tech_names
    assert "Kubernetes" in tech_names
    assert "Engineering Manager" in role_names


def test_tags_are_unique_per_pattern():
    """Each pattern should only match once even if it appears multiple times in the text."""
    job = _make_job("Python Developer")
    description = "Python Python Python. We love Python."

    with patch("app.workers.job_analyser.TECH_STACK_TAGS", TECH), patch(
        "app.workers.job_analyser.ROLE_TYPE_TAGS", ROLE
    ):
        tags = _extract_tags(job, description)

    python_tags = [t for t in tags if t.name == "Python"]
    assert len(python_tags) == 1


def test_tag_job_id_is_set_correctly():
    job = _make_job("Engineering Manager", job_id=42)
    description = "We use Python."

    with patch("app.workers.job_analyser.TECH_STACK_TAGS", TECH), patch(
        "app.workers.job_analyser.ROLE_TYPE_TAGS", ROLE
    ):
        tags = _extract_tags(job, description)

    assert all(t.job_id == 42 for t in tags)


def test_case_insensitive_matching():
    job = _make_job("engineering manager")
    description = "we use python and fastapi."

    with patch("app.workers.job_analyser.TECH_STACK_TAGS", TECH), patch(
        "app.workers.job_analyser.ROLE_TYPE_TAGS", ROLE
    ):
        tags = _extract_tags(job, description)

    names = {t.name for t in tags}
    assert "Python" in names
    assert "FastAPI" in names
    assert "Engineering Manager" in names
