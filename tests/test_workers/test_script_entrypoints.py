def test_job_scraper_import_safe() -> None:
    from app.workers import job_scraper

    assert callable(getattr(job_scraper, "main", None))


def test_job_analyser_import_safe() -> None:
    from app.workers import job_analyser

    assert callable(getattr(job_analyser, "main", None))
