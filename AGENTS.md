# Repository Guidelines

## Project Structure & Module Organization
- `app/` holds the FastAPI application code (routers, handlers, models, db, utils).
- `tests/` contains pytest suites for routers and scrapers.
- `alembic/` stores migration scripts and config.
- `static/` contains icons and other static assets.
- `migration/` includes legacy scripts/notes for database setup.

## Layering & Ownership (Separation of Concerns)

Keep a clear boundary between layers:

- **Routers (`app/routers/`)**: HTTP concerns only.
  - Parse/validate request inputs (Pydantic models, query params).
  - Call handlers/services.
  - Return response models.
  - No raw SQL/`select()` construction in routers.
  - No business logic beyond trivial wiring.

- **Handlers (`app/handlers/`)**: database access and persistence.
  - Own all `select()/where()/join()` query construction and DB writes.
  - Provide `save()` / `save_all()` methods that perform upserts and `flush()` as needed.
  - **Do not call `commit()` inside handlers.** Transaction boundaries are owned by the caller (workers/routers/services), which batch commits for performance and atomicity.
  - Accept filter/pagination objects; return model instances or read DTOs.
  - Do not import FastAPI objects.

- **Models (`app/models/`)**: SQLModel/Pydantic schemas only.
  - Domain fields, validation, small domain methods (state transitions).
  - No DB session usage.

- **Workers (`app/workers/`)**: orchestration.
  - Batch processing, commit strategy, metrics/logging around jobs.
  - Use handlers for DB operations.

Response/request schemas:
- Define shared API schemas under `app/schemas/` (or `app/routers/schemas/`) rather than inside routers.
- Routers may declare lightweight local schemas only when truly single-use and sm

## Build, Test, and Development Commands
- `make requirements`: install dependencies via Poetry for local dev.
- `make start-db`: start the Postgres service via `docker-compose`.
- `make migrations`: run Alembic upgrades to `head`.
- `make main`: run the app with `python3 main.py`.
- `make start`: full local boot (deps, DB, migrations, server).
- `make check`: run all pre-commit hooks and the test suite.
- `docker-compose up`: alternative way to run the whole stack locally.

## Coding Style & Naming Conventions
- Python formatting uses Black (line length 79) and isort (Black profile).
- Linting via flake8 (max line length 120) and pycln for unused imports.
- Type checks run with mypy (SQLAlchemy plugin enabled).
- Tests follow `test_*.py` and `test_*` function naming.

## Testing Guidelines
- Framework: pytest with `pytest-cov`.
- Coverage: `--cov-fail-under=50` and `--cov=app`.
- Run tests with `make pytest` or `poetry run pytest tests`.

## Commit & Pull Request Guidelines
- Commit style in history is short, imperative, and descriptive (e.g., “Add ashby scraper”).
- Keep commits focused; one logical change per commit when possible.
- PRs should include a clear summary, testing notes (`make check` or `make pytest`),
  and any required migration steps. Add screenshots only if a UI change is involved.

## Configuration Tips
- Create `.env` from `.env.sample` before running locally.
- Health check is available at `http://localhost:8000/healthy`.

## ATS Scraper Design Rules

This project supports multiple ATS platforms (Ashby, Greenhouse, Teamtailor, etc.).
Scrapers MUST follow these rules:

- Scrapers must be deterministic:
  - No browser automation
  - No execution of client-side JavaScript
- If job data is not present in the initial HTML or embedded JSON state,
  the scraper must fail cleanly and log the reason.
- Scraper-specific DOM / JSON extraction logic lives in the concrete scraper.
- Location parsing, Europe filtering, and remote detection must live in the base
  `AtsScraper` utilities — never duplicated per scraper.
- Scrapers must not infer or guess data (e.g. country, board IDs).
- Scrapers must return empty results rather than partially-invalid jobs.

## ATS Scraper Factory

- `AtsScraperFactory` selects scrapers based on URL matching via `supports(url)`.
- Scrapers are evaluated in order of specificity.
- `supports()` implementations MUST be conservative and narrowly scoped.
- Each scraper must have:
  - Positive support tests
  - Negative support tests (e.g. Ashby URL must not match Teamtailor).

## Embedded JSON Extraction

Some ATS platforms embed job data in inline `<script>` tags.

Guidelines:
- Do not parse external JS bundles.
- Only extract JSON from inline script tags.
- Prefer explicit JSON assignment markers (e.g. `VAR = {...};`).
- Regex extraction must terminate on the assignment boundary (`};`),
  not on arbitrary semicolons.
- If embedded data cannot be reliably extracted, the scraper must log
  and return no jobs.

## Job URL Construction

- Job URLs must be stable and deterministic.
- If a job URL is not provided by the ATS payload, it may be constructed only
  when the format is explicitly known (e.g. Ashby: `{career_page.url}/{job_id}`).
- If a URL cannot be constructed with certainty, the job must be dropped.

## Typing & mypy

- `parse_job_card()` accepts `object` at the interface level.
- Concrete scrapers must narrow the type explicitly:
  - HTML scrapers: `isinstance(card, bs4.Tag)`
  - JSON scrapers: `isinstance(card, dict)`
- Use runtime checks + `typing.cast`, not `Any` or `# type: ignore`.

## Logging Conventions

- Scrapers must not hardcode their name in log messages.
- Use `cls.__name__` or `self.__class__.__name__` in logs.
- Log reasons for skipping jobs (non-Europe, missing URL, JS-only boards).
