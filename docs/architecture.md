# Architecture & Codebase Map

## Directory Structure

```
/
├── app/                        # Main FastAPI application
│   ├── auth/                   # Authentication (X-User-Id header)
│   ├── db/                     # Database engine/session setup
│   ├── filters/                # Query filter/pagination models
│   ├── handlers/               # Database access layer (all SQL lives here)
│   ├── job_analysis/           # Job description analysis and keyword matching
│   │   └── description_extractors/  # Platform-specific extractors (ATS + LinkedIn)
│   ├── job_scrapers/           # Web scrapers
│   │   └── ats_scrapers/       # Concrete ATS scraper implementations
│   ├── log/                    # Logging configuration
│   ├── models/                 # SQLModel domain models
│   ├── routers/                # FastAPI route handlers
│   ├── schemas/                # Shared API request/response schemas
│   ├── seeds/                  # Data seeding scripts (seed data in seeds/data/)
│   ├── utils/                  # Helpers: location parsing, ATS discovery
│   │   └── locations/          # Country/region/remote detection logic
│   └── workers/                # Background job orchestration
├── alembic/versions/           # Database migrations (date-named)
├── migration/                  # Legacy DB setup scripts/notes
├── tests/                      # pytest suite (fixtures/, test_handlers/, test_routers/, ...)
├── docker/                     # Dockerfiles for local dev
├── static/                     # Static assets (icons, etc.)
├── docs/                       # Documentation
├── main.py                     # FastAPI application entry point
├── pyproject.toml              # Poetry dependency config
├── docker-compose.yml          # Local development stack
├── Makefile                    # Development commands
├── setup.cfg                   # pytest, flake8, mypy, isort config
├── .pre-commit-config.yaml     # Pre-commit hooks
├── alembic.ini                 # Alembic config
└── .env.sample                 # Environment variable template
```

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI 0.115.0 + Uvicorn 0.30.0 |
| ORM | SQLModel 0.0.23 (SQLAlchemy 2.0 + Pydantic 2.x) |
| Database | PostgreSQL 13.4 |
| Migrations | Alembic 1.13.0 |
| Scraping | BeautifulSoup4, tls-client, markdownify |
| Testing | pytest, pytest-cov, httpx, requests-mock, freezegun |
| Package manager | Poetry |
| Python | 3.11 |

## Environment Configuration

`.env` (copied from `.env.sample`):

```env
DB_NAME=fastapi_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=0.0.0.0
DB_PORT=5432
DB_BATCH_SIZE=500
ATS_SCRAPER_DELAY_SECONDS=0.2
```

`app/settings.py` loads these via `pydantic-settings`. The DB connection pool
uses `pool_size=4` and `max_overflow=2`.

## Key Files

| File | Purpose |
|---|---|
| `main.py` | App factory, CORS, exception handlers, router registration |
| `app/settings.py` | Pydantic-settings config loaded from `.env` |
| `app/db/` | Engine, session factory, session dependency |
| `app/models/base_model.py` | Base class with `created_at`, `updated_at`, `deleted_at` |
| `app/handlers/job.py` | Job CRUD, upsert, user-scoped filtering |
| `app/handlers/job_tag.py` | Tag persistence: `replace_tags()`, `get_tags_for_jobs()` |
| `app/handlers/career_page.py` | Career page management |
| `app/handlers/worker_run.py` | Worker run tracking |
| `app/models/job_tag.py` | `JobTag` table, `TagCategory` enum, `JobTagRead` schema |
| `app/search_profile.py` | Keyword and tag patterns (`TECH_STACK_TAGS`, `ROLE_TYPE_TAGS`) |
| `app/workers/sync_ats.py` | ATS scraping orchestration |
| `app/workers/sync_linkedin.py` | LinkedIn scraping orchestration |
| `app/workers/job_analyser.py` | Remote detection, keyword matching, tag extraction |
| `app/job_scrapers/ats_scraper_factory.py` | ATS scraper selection factory |
| `app/job_scrapers/ats_scraper_base.py` | Abstract base for all ATS scrapers |
| `app/utils/ats_discovery.py` | Detect ATS platform from a career page URL |
| `app/utils/locations/` | Country resolution, Europe filtering, remote detection |
| `tests/conftest.py` | Shared pytest fixtures |
