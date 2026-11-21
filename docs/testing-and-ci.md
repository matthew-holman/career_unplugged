# Testing & CI

## Running Tests

```bash
make pytest
# or
poetry run pytest tests --cov-config=.coveragerc --cov-fail-under=50 --cov=app
```

## Test Database & Fixtures

Tests use a separate `_test`-suffixed PostgreSQL database. Fixtures in `tests/conftest.py`:

| Fixture | Scope | Purpose |
|---|---|---|
| `connection` | session | Raw DB connection |
| `setup_db` | function | Creates/drops tables |
| `db_session` | function | Transactional session, rolled back after each test |
| `client` | function | `TestClient` with the FastAPI app + fake DB |
| `test_user` | function | Default `User` |
| `auth_headers` | function | `{"X-User-Id": "1"}` |
| `authed_client` | function | `TestClient` + auth headers |

Static test data lives in `tests/fixtures/`.

## CI (GitHub Actions)

Pipeline: `.github/workflows/ci.yml`. Both jobs must pass on every PR.

- **lint**: Python 3.11 + Poetry, then all pre-commit hooks (isort, black, pycln,
  flake8, mypy, bandit, pyupgrade).
- **test**: Postgres 13.4-alpine service, Alembic migrations, then pytest with coverage.
