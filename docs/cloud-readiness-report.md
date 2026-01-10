# Cloud Readiness & Maintainability Report

## 1) Current runtime entrypoints

**How the app is started today**
- `main.py` runs the FastAPI app via Uvicorn (`uvicorn.run(...)`), with reload enabled when run directly. See `main.py`.
- `make main` runs `python3 main.py`. See `Makefile`.
- `docker-compose.yml` starts the API container and runs `make migrations && make main` on container start. See `docker-compose.yml`.

**How scraping jobs are executed today**
- `app/job_scraper.py` is a script-style entrypoint that runs LinkedIn + ATS scrapers and persists jobs. It is not hooked into the FastAPI app lifecycle or any scheduler. See `app/job_scraper.py`.
- `app/job_analyser.py` is a script that immediately executes analysis logic at import time (no `if __name__ == "__main__":` guard). See `app/job_analyser.py`.

**How DB/migrations are applied today**
- `make migrations` runs `alembic upgrade head`. See `Makefile` and `alembic/env.py`.
- Docker Compose runs migrations every time the API container starts. See `docker-compose.yml`.

## 2) Top 10 issues (ranked by impact and effort)

1) **No scheduled job execution path** (High impact / Low effort)
   - Scrapers run only if `app/job_scraper.py` is executed manually; no scheduler or cloud job runner is defined.
   - See `app/job_scraper.py`.

2) **Analysis script executes at import time** (High impact / Low effort)
   - `app/job_analyser.py` runs on import; this is dangerous in production and difficult to control/retry.
   - See `app/job_analyser.py`.

3) **No notification/alert pipeline** (High impact / Medium effort)
   - There is no integration for email/Slack/push to notify about “interesting jobs”.
   - See `app/job_scraper.py` and `config.py`.

4) **Tests rely on live network without fixtures** (High impact / Medium effort)
   - Scraper tests hit live job boards; network flakiness will break CI and makes debugging harder.
   - See `tests/job_scrapers/ats_scrapers/*`.

5) **CI Python version mismatch** (High impact / Low effort)
   - CI uses Python 3.9 but `pyproject.toml` specifies `>=3.10`. This can hide runtime issues.
   - See `.github/workflows/ci.yml` and `pyproject.toml`.

6) **Dockerfile is dev-focused, not production-ready** (Medium impact / Medium effort)
   - Copies `.env` into the image and runs `make` steps meant for local dev; no proper production entrypoint.
   - See `docker/local-dev.Dockerfile` and `docker-compose.yml`.

7) **Migrations run on every app start** (Medium impact / Low effort)
   - Doing `alembic upgrade head` at app startup is risky and slows boot; should be a separate release step.
   - See `docker-compose.yml`.

8) **Configuration is split and non-standardized** (Medium impact / Medium effort)
   - Runtime config is split across `.env`, `app/settings.py`, and `config.py` for scraper logic.
   - See `app/settings.py` and `config.py`.

9) **Logging is inconsistent and not structured** (Medium impact / Low effort)
   - Two logging utilities (`app/log/log.py` and `app/utils/log_wrapper.py`) and no JSON/structured logging.
   - See `app/log/log.py` and `app/utils/log_wrapper.py`.

10) **Dependency/version drift and compatibility risk** (Medium impact / Medium effort)
   - Inconsistent dependency specs between `pyproject.toml` and `setup.cfg`. Older Alembic/Uvicorn versions.
   - See `pyproject.toml` and `setup.cfg`.

## 3) Recommendations with rationale

- **Introduce explicit task entrypoints (CLI commands) for scraping and analysis.**
  - Add `app/cli.py` or a `typer`/`click` CLI with `scrape` and `analyse` commands. This makes scheduled execution explicit and testable.

- **Add a scheduler-friendly worker mode.**
  - Provide a `python -m app.job_scraper` or `make scrape` entrypoint; do the same for analysis (move logic under `main()` guard).

- **Add a notification output path.**
  - Start with a simple Slack webhook or email output. Optionally send a daily digest based on a query over new jobs.

- **Introduce deterministic scraper fixtures.**
  - Store HTML fixtures under `tests/job_scrapers/fixtures/` and use `requests-mock` to avoid live network calls.

- **Make Docker production-ready.**
  - Add a `Dockerfile` for production (no `.env` baked in). Use `uvicorn` with `--host 0.0.0.0 --port 8000` or `gunicorn -k uvicorn.workers.UvicornWorker`.

- **Separate DB migrations from app startup.**
  - Create a “release” step (CI/CD job or one-off container) to run `alembic upgrade head`.

- **Unify config management.**
  - Keep all runtime config in `app/settings.py` and convert `config.py` to purely data/seed inputs, or make it configurable via env.

- **Normalize logging.**
  - Replace multiple wrappers with a single logging setup and support JSON formatting for cloud logs.

- **Align CI with runtime Python version.**
  - Update CI to use Python 3.10+ to match `pyproject.toml`.

- **Create a basic cloud deployment template.**
  - Provide a `docker-compose.prod.yml` or a cloud-specific template (ECS/Cloud Run/Render) to run API + scheduled scraper.

## 4) Do now / Do next / Do later

**Do now (fast, high impact)**
- Add explicit CLI entrypoints for `scrape` and `analyse` (`app/job_scraper.py`, `app/job_analyser.py`).
- Update CI Python version to 3.10+. See `.github/workflows/ci.yml`.
- Add a simple notification output (Slack webhook or email) as a placeholder.

**Do next (medium effort)**
- Add HTML/JSON fixtures for scrapers and switch tests to `requests-mock`.
- Separate migrations into a deploy step and remove `make migrations` from app start.
- Add a production Dockerfile + entrypoint.

**Do later (larger changes)**
- Migrate to managed scheduling (Cloud Scheduler/ECS Scheduled Task) for scraping and analysis.
- Add structured logging + error reporting (Sentry).
- Add metrics (Prometheus/OpenTelemetry) and alerting.

## 5) Risks / unknowns

- **Job scraper/analysis are side-effectful scripts** and may be brittle in a containerized environment. See `app/job_scraper.py` and `app/job_analyser.py`.
- **Live network tests can fail unpredictably**, impacting CI stability. See `tests/job_scrapers/ats_scrapers/*`.
- **CI uses Python 3.9 while runtime is 3.10+**, which can mask compatibility issues. See `.github/workflows/ci.yml`.
- **Dependency versions in `setup.cfg` conflict with `pyproject.toml`**, which can lead to tooling inconsistencies.

## 6) Target cloud architecture

**Containerization approach**
- Use a production `Dockerfile` with:
  - Multi-stage build or slim runtime base.
  - No `.env` baked into the image.
  - `uvicorn`/`gunicorn` entrypoint.
- Keep `docker/local-dev.Dockerfile` for local development.

**Environment configuration strategy**
- Use `app/settings.py` + environment variables. Keep `.env` for local dev only.
- Use cloud secret store (AWS Secrets Manager / GCP Secret Manager / Render secrets) for production.

**Scheduling approach**
- **Short term:** a separate container command `python -m app.job_scraper` invoked by cron (K8s CronJob, ECS Scheduled Task, or Cloud Run + Scheduler).
- **Longer term:** introduce a worker queue (Celery/RQ) with a scheduler (Celery Beat, APScheduler) if scraping frequency increases.

**Notification approach**
- **First step:** Slack webhook or email digest triggered after `run_ats_scrapers` completes.
- **Later:** store notification state to avoid duplicates and send summaries by source or keywords.

**Observability**
- Structured logging (JSON) with correlation IDs for jobs.
- Error reporting via Sentry or Honeybadger.
- Basic metrics (scrape count, job count, parse failures) via Prometheus/OpenTelemetry.

## 7) Dependency and upgrade plan

**What looks outdated or risky**
- Uvicorn `0.20.0` is old; update to a recent 0.30+ series.
- Alembic `1.9.0` is older; upgrade to 1.13+.
- `setup.cfg` declares `python = "^3.9"` under `[tool.poetry.dependencies]`, conflicting with `pyproject.toml`.
- SQLModel `0.0.16` is compatible with Pydantic v2 but is behind current versions.

**Recommended upgrade approach (minimize breakage)**
1) **Align Python version in CI and tooling** to 3.10 or 3.11.
2) **Update FastAPI + Starlette + Uvicorn** together in a single PR, running `make check`.
3) **Upgrade Alembic** and run migration generation/upgrade tests.
4) **Upgrade SQLModel cautiously** and run tests for model validation (`app/models/*`).
5) **Pydantic v2 considerations:**
   - Update legacy `class Config` patterns to `ConfigDict` and `model_config` (example: `app/settings.py`).
   - Verify `BaseModel` config compatibility (`app/models/base_model.py`).

**Stay or upgrade?**
- **Upgrade within the current major versions** (FastAPI 0.110 -> 0.11x, SQLModel 0.0.16 -> latest 0.0.x, Alembic 1.9 -> 1.13) to minimize breaking changes.
- Avoid jumping to major changes (e.g., if SQLModel introduces major API changes) until after tests/fixtures are in place.

## 8) Testing and CI recommendations

**Testing gaps**
- Scraper coverage depends on live sites; add fixtures and mock HTTP responses.
- No tests for job analysis logic (`app/job_analyser.py`).

**How to add fixtures**
- Save HTML responses under `tests/job_scrapers/fixtures/`.
- Use `requests-mock` to return fixture responses for `AtsScraper._fetch_page`.
- Add unit tests that parse HTML using `BeautifulSoup` and verify extraction fields.

**Minimal CI pipeline**
- Use Python 3.10/3.11.
- Run: `make check` (pre-commit + pytest).
- Keep DB-backed tests, but explicitly disable network tests by default (`-m "not network"`).

## Checklist

- [ ] Add CLI entrypoints for `scrape` and `analyse`.
- [ ] Add a scheduled job runner (cron or managed scheduler).
- [ ] Introduce a Slack/email notification step.
- [ ] Add HTML/JSON fixtures for scrapers and mock HTTP responses.
- [ ] Align CI Python version with `pyproject.toml`.
- [ ] Split migrations into a release/deploy step.
- [ ] Add a production Dockerfile and entrypoint.
- [ ] Consolidate configuration into `app/settings.py` and env vars.
- [ ] Normalize logging and add structured logs.
- [ ] Upgrade dependencies in a staged plan.
