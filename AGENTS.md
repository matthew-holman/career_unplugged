# Repository Guidelines — Career Unplugged

Career Unplugged is a **FastAPI job scraping and analysis platform**. It scrapes
listings from ATS platforms (Greenhouse, Ashby, Lever, Teamtailor, etc.) and
LinkedIn, deduplicates them in PostgreSQL, analyses them for remote status,
keyword matches and tags, and exposes a REST API for browsing jobs and tracking
application state.

This file holds the rules that apply to all work in the repo. Area-specific
detail lives in `docs/`. Read the relevant doc before working in that area:

| Doc | Read when working on |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Directory layout, tech stack, key files |
| [`docs/ats-scrapers.md`](docs/ats-scrapers.md) | Anything under `app/job_scrapers/` or `app/utils/ats_discovery.py` |
| [`docs/database.md`](docs/database.md) | Models, handlers, migrations, upserts, batching |
| [`docs/api.md`](docs/api.md) | Routers, auth, API responses |
| [`docs/testing-and-ci.md`](docs/testing-and-ci.md) | Test fixtures, CI pipeline |

---

## Layering & Ownership (Strict Separation of Concerns)

Never mix responsibilities across layers.

- **Routers (`app/routers/`)**: HTTP concerns only.
  - Parse/validate input, call handlers/workers, return response models.
  - No raw SQL or `select()`/`where()` construction; no business logic beyond trivial wiring.
  - Get sessions via `Depends`, never by importing SQLAlchemy/session objects directly.
- **Handlers (`app/handlers/`)**: all database access.
  - Own all `select()`/`where()`/`join()` construction, upserts and `flush()`.
  - Provide `save()` / `save_all()` methods for upserts.
  - **Never call `commit()`**. Transaction boundaries belong to the caller.
  - Accept filter/pagination objects; return model instances or read DTOs.
  - Do not import FastAPI objects.
- **Models (`app/models/`)**: SQLModel/Pydantic schemas only.
  - Domain fields, validation, small domain methods (e.g. `mark_true_remote()`).
  - No DB session usage.
- **Workers (`app/workers/`)**: orchestration.
  - Batch processing, commit strategy, logging/metrics. Use handlers for DB work.
  - Own `session.commit()`.
- **Schemas (`app/schemas/`)**: shared API request/response DTOs.
  - Routers may define lightweight local schemas only when truly single-use and small.

Records are **soft-deleted** (`deleted_at`, or `active=False` for career pages).
Never hard-delete, and always exclude soft-deleted rows in queries.

---

## Development Commands

```bash
make start                    # requirements + start-db + migrations + main
make requirements             # Install deps via Poetry
make start-db                 # Start Postgres via docker-compose
make migrations               # alembic upgrade head
make main                     # Run the FastAPI app

make check                    # All pre-commit hooks + test suite (run before pushing)
make run-all-pre-commit-hooks
make pytest                   # Test suite with coverage

make sync-ats | sync-linkedin | sync-all | analyse   # Run workers
make create-user NAME=... EMAIL=...
make seed-career-pages
```

Before running locally, copy `.env.sample` to `.env` (settings load via
`pydantic-settings` in `app/settings.py`).

---

## Coding Style & Conventions

- Python 3.11, Poetry.
- **Black** line length 88 and **isort** (Black profile, 88), enforced by
  pre-commit. (`pyproject.toml` still says 79, but pre-commit passes `--line-length=88`.)
- **flake8** max line length 120, with print statements flagged (T001). **pycln**
  removes unused imports. **bandit** and **pyupgrade** also run in pre-commit.
- **mypy** with the SQLAlchemy plugin. Every function must be typed.
  Narrow with `isinstance()` and `typing.cast`. **Never use `Any` or `# type: ignore`.**
- Naming: `snake_case` functions/variables, `PascalCase` classes,
  `UPPER_SNAKE_CASE` constants. API response fields are `camelCase` via the
  Pydantic `alias_generator`.
- Imports: stdlib → third-party → local; no wildcard imports.

---

## Testing

- pytest + pytest-cov. Coverage floor: `--cov-fail-under=50 --cov=app`.
- Files are `test_*.py`, functions are `test_*`.
- Run with `make pytest`. Fixtures and CI details are in `docs/testing-and-ci.md`.

---

## Commit & Pull Request Guidelines

- Commit messages are short, imperative and descriptive (e.g. "Add ashby scraper").
- One logical change per commit when possible.
- PRs include a clear summary, testing notes (`make check` / `make pytest`
  passes), and migration steps if the schema changed. Add screenshots only for UI changes.
