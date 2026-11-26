# Database

PostgreSQL via SQLModel. `job`, `user` and `worker_run` inherit `created_at`,
`updated_at` and `deleted_at` from `app/models/base_model.py`. `career_page`,
`user_job` and `job_tag` extend `SQLModel` directly and have no audit fields.

## Core Tables

**`job`**: job listings
- `id`, `title`, `company`, `country`, `city`
- `listing_remote` (`RemoteStatus`), `listing_date`, `true_remote` (bool), `analysed` (bool)
- `positive_keyword_match`, `negative_keyword_match` (bool)
- `source_url` (unique), `career_page_id` (FK)

**`career_page`**: ATS career pages being scraped
- `id`, `company_name`, `url` (unique), `active` (bool)
- `deactivated_at`, `last_status_code`, `last_synced_at`
- `relevance` (`CareerPageRelevance`): set by each ATS scan from where the
  page's jobs are (`app/utils/locations/page_relevance.py`). The ATS sync only
  rescans low-relevance pages every `RELEVANCE_RESCAN_DAYS`
  (`app/search_profile.py`). `relevance_locked` pins a manually set value.
- `scraper_status` (`CareerPageScraperStatus`: `UNCHECKED` / `SUPPORTED` /
  `UNSUPPORTED`) and `scraper_checked_at`: set by each ATS scan that fetches the
  page. Pages no scraper matched are only re-fetched every
  `UNSUPPORTED_RECHECK_DAYS`, or on a sync with `include_unsupported`. Custom
  careers sites found through LinkedIn apply links
  (`discover_custom_career_page` in `app/utils/ats_discovery.py`) start
  `UNCHECKED`.

**`user`**: `id`, `name`, `email` (unique, indexed)

**`user_job`**: user ↔ job interaction
- `user_id` (FK, PK), `job_id` (FK, PK), `applied` (bool), `ignored` (bool)

**`worker_run`**: background job execution tracking
- `id`, `run_id` (unique, indexed), `worker_name`, `status` (`WorkerRunStatus`)
- `started_at`, `finished_at`, `summary` (JSONB), `errors` (JSONB)

**`job_tag`**: tags extracted during analysis, categorised for frontend display
- `id`, `job_id` (FK, indexed), `name`, `category` (`TagCategory`)
- UNIQUE on `(job_id, name)`
- No audit fields. Tags are replaced wholesale on each analysis run via
  `JobTagHandler.replace_tags()`.
- Patterns configured in `app/search_profile.py` (`TECH_STACK_TAGS`, `ROLE_TYPE_TAGS`).

## Enums

- `RemoteStatus`: UNKNOWN, ONSITE, HYBRID, REMOTE
- `Source`: LINKEDIN, TEAMTAILOR, GREENHOUSE_BOARD, GREENHOUSE_EMBEDDED, ASHBY,
  LEVER, RECRUITEE, RIPPLING, PERSONIO, HIBOB, BAMBOO, WORKABLE, JOBYLON
- `WorkerRunStatus`: PENDING, RUNNING, SUCCEEDED, FAILED
- `JobType`: FULL_TIME, PART_TIME, INTERNSHIP, CONTRACT, TEMPORARY
- `TagCategory`: TECH_STACK, ROLE_TYPE
- `CareerPageRelevance`: UNKNOWN, TARGET, REMOTE_OUTSIDE_EUROPE, EUROPE_ONSITE,
  OUTSIDE_EUROPE

## Soft Deletes

For models with `deleted_at`, call `.delete()` to set it. Never hard-delete.
Queries must exclude soft-deleted rows. `career_page` uses `active` /
`deactivated_at` instead.

## Upsert Strategy

- Job deduplication uses `ON CONFLICT DO UPDATE` on `(source, source_url)`.
- Excluded from the update set: `created_at`, `updated_at`, `deleted_at`, `analysed`.

## Batching

- `DB_BATCH_SIZE` (default 500, from env) controls batch flush size.
- Workers use `flush_pending_jobs()` / `flush_pending_pages()` for batched upserts.
- Handlers call `session.flush()` within a batch. Workers call `session.commit()` after each batch.

## Migrations (Alembic)

- Config: `alembic.ini`; files in `alembic/versions/`.
- Naming: `YYYY-MM-DD_<revision>_<slug>.py`.
- To add columns/tables:
  1. `poetry run alembic revision --autogenerate -m "description"`
  2. Review the generated file.
  3. `make migrations` (runs `alembic upgrade head`).
