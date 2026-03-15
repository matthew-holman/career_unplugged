# CLAUDE.md — Career Unplugged Codebase Guide

This file provides AI assistants with a comprehensive understanding of the Career Unplugged codebase: its structure, conventions, workflows, and rules to follow when making changes.

---

## Project Overview

Career Unplugged is a **FastAPI-based job scraping and analysis platform**. It:
- Scrapes job listings from multiple ATS platforms (Greenhouse, Ashby, Lever, Teamtailor, etc.) and LinkedIn
- Stores and deduplicates jobs in PostgreSQL
- Analyses jobs for remote status and keyword matches
- Exposes a REST API for users to browse/filter jobs and track their application state

---

## Directory Structure

```
/
├── app/                        # Main FastAPI application
│   ├── auth/                   # Authentication (X-User-Id header)
│   ├── db/                     # Database engine/session setup
│   ├── filters/                # Query filter/pagination models
│   ├── handlers/               # Database access layer (all SQL lives here)
│   ├── job_analysis/           # Job description analysis and keyword matching
│   │   └── description_extractors/  # Platform-specific extractors (9 ATS + LinkedIn)
│   ├── job_scrapers/           # Web scrapers
│   │   └── ats_scrapers/       # Concrete ATS scraper implementations
│   ├── log/                    # Logging configuration
│   ├── models/                 # SQLModel domain models
│   ├── routers/                # FastAPI route handlers
│   ├── schemas/                # Shared API request/response schemas
│   ├── seeds/                  # Data seeding scripts
│   ├── utils/                  # Helpers: location parsing, ATS discovery
│   │   └── locations/          # Country/region/remote detection logic
│   └── workers/                # Background job orchestration
├── alembic/                    # Database migrations
│   └── versions/               # Migration files (date-named)
├── tests/                      # pytest test suite
│   ├── fixtures/               # Test data fixtures
│   ├── test_handlers/
│   ├── test_job_analysis/
│   ├── test_job_scrapers/
│   ├── test_routers/
│   ├── test_utils/
│   └── test_workers/
├── docker/                     # Dockerfiles for local dev
├── static/                     # Static assets (icons, etc.)
├── docs/                       # Documentation files
├── main.py                     # FastAPI application entry point
├── pyproject.toml              # Poetry dependency config
├── docker-compose.yml          # Local development stack
├── Makefile                    # Development commands
├── setup.cfg                   # pytest, flake8, mypy, isort config
├── .pre-commit-config.yaml     # Pre-commit hooks
├── alembic.ini                 # Alembic migration config
└── .env.sample                 # Environment variable template
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI 0.115.0 + Uvicorn 0.30.0 |
| ORM | SQLModel 0.0.23 (SQLAlchemy 2.0 + Pydantic 2.x) |
| Database | PostgreSQL 13.4 |
| Migrations | Alembic 1.13.0 |
| Scraping | BeautifulSoup4, tls-client, markdownify |
| Testing | pytest, pytest-cov, httpx, requests-mock, freezegun |
| Formatting | Black (88 chars), isort (Black profile) |
| Linting | flake8 (120 chars max), pycln, bandit |
| Type checking | mypy with SQLAlchemy plugin |
| Package manager | Poetry |
| Python version | 3.11 |

---

## Layered Architecture — Strict Separation of Concerns

The codebase enforces a **four-layer architecture**. Never mix responsibilities across layers.

### Routers (`app/routers/`)
- HTTP concerns **only**: parse request, validate input, call handlers/workers, return response.
- No raw SQL, no `select()`/`where()` construction.
- No business logic beyond trivial wiring.
- Do not import SQLAlchemy or session objects directly — use `Depends`.

### Handlers (`app/handlers/`)
- **Own all database access**: `select()`, `where()`, `join()`, `upsert`, `flush()`.
- Provide `save()` / `save_all()` methods for upserts.
- **Never call `commit()`** — transaction boundaries are owned by workers/routers.
- Accept filter/pagination objects; return model instances or DTOs.
- Do not import FastAPI objects.

### Models (`app/models/`)
- SQLModel/Pydantic schemas only.
- Domain fields, validation, and small domain methods (state transitions like `mark_true_remote()`).
- No DB session usage.

### Workers (`app/workers/`)
- Orchestration layer: batch processing, commit strategy, logging, metrics.
- Use handlers for all DB operations.
- Responsible for `session.commit()`.

### Schemas (`app/schemas/`)
- Shared API request/response DTOs.
- Routers may define lightweight local schemas only for truly single-use, small cases.

---

## Database Schema

### Core Tables

**`job`** — Job listings
- `id`, `title`, `company`, `country`, `city`
- `listing_remote` (enum: UNKNOWN/ONSITE/HYBRID/REMOTE)
- `listing_date`, `true_remote` (bool), `analysed` (bool)
- `positive_keyword_match`, `negative_keyword_match` (bool)
- `source_url` (unique), `career_page_id` (FK)
- `created_at`, `updated_at`, `deleted_at`

**`career_page`** — ATS career pages being scraped
- `id`, `company_name`, `url` (unique), `active` (bool)
- `deactivated_at`, `last_status_code`, `last_synced_at`
- `created_at`, `updated_at`, `deleted_at`

**`user`** — Platform users
- `id`, `name`, `email` (unique, indexed)
- `created_at`, `updated_at`, `deleted_at`

**`user_job`** — User ↔ job interaction mapping
- `user_id` (FK, PK), `job_id` (FK, PK)
- `applied` (bool), `ignored` (bool)

**`worker_run`** — Background job execution tracking
- `id`, `run_id` (unique, indexed), `worker_name`
- `status` (enum: PENDING/RUNNING/SUCCEEDED/FAILED)
- `started_at`, `finished_at`, `summary` (JSONB), `errors` (JSONB)

### Enums
- `RemoteStatus`: UNKNOWN, ONSITE, HYBRID, REMOTE
- `Source`: LINKEDIN, TEAMTAILOR, GREENHOUSE_BOARD, GREENHOUSE_EMBEDDED, ASHBY, LEVER, RECRUITEE, RIPPLING, PERSONIO, HIBOB, BAMBOO
- `WorkerRunStatus`: PENDING, RUNNING, SUCCEEDED, FAILED
- `JobType`: FULL_TIME, PART_TIME, INTERNSHIP, CONTRACT, TEMPORARY

### Soft Deletes
All tables have a `deleted_at` nullable DateTime. Call `.delete()` to set the timestamp — never hard-delete records. Queries must exclude soft-deleted rows.

### Upsert Strategy
- Job deduplication uses `ON CONFLICT DO UPDATE` on `(source, source_url)`.
- Excluded from update: `created_at`, `updated_at`, `deleted_at`, `analysed`.

---

## API Routes

| Method | Path | Description |
|---|---|---|
| GET | `/` | Redirect to `/docs` |
| GET | `/healthy` | Health check |
| GET | `/job/` | List jobs (with filters) |
| GET | `/job/{job_id}` | Get single job with user state |
| PUT | `/job/{job_id}/state` | Update user job state (applied/ignored) |
| POST | `/user/` | Create user |
| GET | `/user/` | Get current user |
| POST | `/sync/ats` | Trigger ATS scraping |
| POST | `/sync/linkedin` | Trigger LinkedIn scraping |
| POST | `/sync/all` | Trigger all sync jobs |
| GET | `/dashboard/` | Dashboard statistics |
| GET | `/career-pages/` | List career pages |
| POST | `/career-pages/` | Add career page |
| GET | `/worker-runs/` | List worker run statuses |
| GET | `/worker-runs/{run_id}` | Get specific worker run |
| GET | `/regions/` | Available regions/locations |

---

## Authentication

- Header-based: `X-User-Id: <integer>`
- Extracted by `get_current_user()` in `app/auth/current_user.py`
- Returns HTTP 403 if header is missing or invalid

---

## Development Commands (Makefile)

```bash
# Setup
make requirements           # Install deps via Poetry
make start-db               # Start Postgres via docker-compose
make migrations             # Run Alembic migrations to head
make main                   # Run FastAPI app

# Full stack
make start                  # requirements + start-db + migrations + main

# Code quality
make check                  # Run all pre-commit hooks + test suite
make run-all-pre-commit-hooks

# Testing
make pytest                 # Run test suite with coverage

# Workers (run individually)
make sync-ats               # Scrape ATS career pages
make sync-linkedin          # Scrape LinkedIn
make sync-all               # All sync workers
make analyse                # Run job analyser

# Data management
make create-user            # Create user: make create-user NAME=... EMAIL=...
make seed-career-pages      # Populate career pages from seed data
```

---

## Environment Configuration

Copy `.env.sample` to `.env` before running locally:

```env
DB_NAME=fastapi_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=0.0.0.0
DB_PORT=5432
DB_BATCH_SIZE=500
ATS_SCRAPER_DELAY_SECONDS=0.2
```

Key settings in `app/settings.py`:
- Loaded from `.env` at project root via `pydantic-settings`
- DB connection pool: `pool_size=4`, `max_overflow=2`
- `DB_BATCH_SIZE=500` controls batch flush size in workers

---

## Coding Style & Conventions

### Formatting
- **Black**: line length 88 (configured), enforced via pre-commit
- **isort**: Black profile, line length 88
- **flake8**: max line length 120, T001 (print statements) enabled
- **pycln**: removes unused imports

### Naming
- Variables and functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- API response fields: `camelCase` (via Pydantic alias_generator)

### Type Annotations
- All functions must be typed; mypy runs with `--strict`-adjacent settings
- SQLAlchemy mypy plugin is enabled (`plugins = sqlalchemy.ext.mypy.plugin`)
- Use `isinstance()` for type narrowing; **never use `Any` or `# type: ignore`**

### Imports
- Organised by isort (Black profile): stdlib → third-party → local
- No wildcard imports

---

## Testing Guidelines

### Framework
- pytest with pytest-cov
- Minimum coverage: **50%** (`--cov-fail-under=50 --cov=app`)

### Test Database
- Separate `_test`-suffixed PostgreSQL database
- Fixtures in `tests/conftest.py`:
  - `connection` (session-scoped): raw DB connection
  - `setup_db` (function-scoped): creates/drops tables
  - `db_session` (function-scoped): transactional session, rolls back after each test
  - `client`: `TestClient` with FastAPI app + fake DB
  - `test_user`: default User fixture
  - `auth_headers`: `{"X-User-Id": "1"}` headers
  - `authed_client`: `TestClient` + auth headers

### Running Tests
```bash
make pytest
# or
poetry run pytest tests --cov-config=.coveragerc --cov-fail-under=50 --cov=app
```

### File Naming
- Test files: `test_*.py`
- Test functions: `test_*`

---

## ATS Scraper Rules

All scrapers under `app/job_scrapers/ats_scrapers/` must follow these rules:

### Determinism
- **No browser automation** — no Selenium, Playwright, or JS execution
- **No inference** — never guess country, board IDs, or job URLs
- If data is absent from initial HTML or embedded JSON: fail cleanly and log the reason
- Return empty results rather than partially-invalid jobs

### Factory Pattern
- `AtsScraperFactory` selects scrapers via `supports(url)` evaluated in specificity order
- `supports()` must be **conservative and narrowly scoped**
- Each scraper must have positive AND negative `supports()` tests

### Embedded JSON Extraction
- Only extract JSON from **inline `<script>` tags** — never parse external JS bundles
- Prefer explicit JSON assignment markers (e.g. `VAR = {...};`)
- Regex extraction must terminate at assignment boundary (`};`), not arbitrary semicolons
- If embedded data cannot be reliably extracted: log and return no jobs

### Job URL Construction
- URLs must be **stable and deterministic**
- Only construct a URL when the format is explicitly known (e.g. Ashby: `{career_page.url}/{job_id}`)
- If URL cannot be constructed with certainty: **drop the job**

### Type Narrowing in Scrapers
- `parse_job_card()` accepts `object` at the interface level
- HTML scrapers: narrow with `isinstance(card, bs4.Tag)`
- JSON scrapers: narrow with `isinstance(card, dict)`
- Use runtime checks + `typing.cast`, not `Any` or `# type: ignore`

### Location & Remote Detection
- Location parsing, Europe filtering, and remote detection live in the base `AtsScraper` utilities — never duplicated per scraper

### Logging
- Never hardcode the scraper class name in log messages
- Use `cls.__name__` or `self.__class__.__name__`
- Log reasons for skipping jobs (non-Europe, missing URL, JS-only boards)

---

## Database Migrations (Alembic)

- Config: `alembic.ini`
- Migrations directory: `alembic/versions/`
- Naming convention: `YYYY-MM-DD_<revision>_<slug>.py`
- Run: `make migrations` (runs `alembic upgrade head`)

When adding new columns or tables:
1. Create a migration: `poetry run alembic revision --autogenerate -m "description"`
2. Review the generated file
3. Run `make migrations`

---

## CI/CD (GitHub Actions)

Pipeline: `.github/workflows/ci.yml`

**lint** job:
1. Install Python 3.11 + Poetry
2. Run all pre-commit hooks (isort, black, pycln, flake8, mypy, bandit, pyupgrade)

**test** job:
1. Start Postgres 13.4-alpine service
2. Run Alembic migrations
3. Run pytest with coverage

Both jobs must pass on every PR.

---

## Background Batching

- `DB_BATCH_SIZE=500` (configurable via env)
- Workers use `flush_pending_jobs()` / `flush_pending_pages()` for batched upserts
- Handlers use `session.flush()` within a batch; workers call `session.commit()` after each batch

---

## Key Files Quick Reference

| File | Purpose |
|---|---|
| `main.py` | App factory, CORS, exception handlers, router registration |
| `app/settings.py` | Pydantic-settings config loaded from `.env` |
| `app/db/` | Engine, session factory, session dependency |
| `app/models/base_model.py` | Base class with `created_at`, `updated_at`, `deleted_at` |
| `app/handlers/job.py` | Job CRUD, upsert, user-scoped filtering |
| `app/handlers/career_page.py` | Career page management |
| `app/handlers/worker_run.py` | Worker run tracking |
| `app/workers/sync_ats.py` | ATS scraping orchestration |
| `app/workers/sync_linkedin.py` | LinkedIn scraping orchestration |
| `app/workers/job_analyser.py` | Remote detection + keyword matching |
| `app/job_scrapers/ats_scraper_factory.py` | ATS scraper selection factory |
| `app/job_scrapers/ats_scraper_base.py` | Abstract base for all ATS scrapers |
| `app/utils/ats_discovery.py` | Detect ATS platform from career page URL |
| `app/utils/locations/` | Country resolution, Europe filtering, remote detection |
| `tests/conftest.py` | Shared pytest fixtures |

---

## Commit & PR Guidelines

- Commit messages: short, imperative, descriptive (e.g. `"Add ashby scraper"`, `"Fix LinkedIn location parsing"`)
- One logical change per commit when possible
- PRs must include:
  - Clear summary of changes
  - Testing notes (confirm `make check` or `make pytest` passes)
  - Migration steps if schema changed
  - Screenshots only for UI changes
- Run `make check` before pushing to ensure linting and tests pass
