# API

Routers are registered in `main.py`. The live, authoritative list is the OpenAPI
UI at `/docs` (`/` redirects there).

## Routes

| Method | Path | Description |
|---|---|---|
| GET | `/job/` | List jobs (with filters) |
| GET | `/job/{job_id}` | Get a single job with user state |
| PUT | `/job/{job_id}/state` | Update user job state (applied/ignored) |
| GET | `/user/activity` | Current user's activity |
| GET | `/dashboard/jobs/summary` | Dashboard job statistics |
| GET | `/career-pages/` | List career pages |
| POST | `/career-pages/` | Add a career page |
| GET | `/career-pages/{page_id}` | Get a career page |
| PUT | `/career-pages/{page_id}` | Update a career page |
| POST | `/sync/ats` | Trigger ATS scraping |
| POST | `/sync/linkedin` | Trigger LinkedIn scraping |
| POST | `/sync/all` | Trigger all sync jobs |
| GET | `/worker-runs` | List worker runs |
| GET | `/worker-runs/{worker_run_id}` | Get a worker run |
| GET | `/regions` | Available regions/locations |

## Authentication

- Header-based: `X-User-Id: <integer>`.
- Resolved by `get_current_user()` in `app/auth/current_user.py`.
- Returns HTTP 403 if the header is missing or invalid.

## Response Conventions

- Response fields are `camelCase` via the Pydantic `alias_generator`.
- Shared request/response schemas live in `app/schemas/`.
