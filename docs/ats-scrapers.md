# ATS Scraper Rules

All scrapers under `app/job_scrapers/ats_scrapers/` must follow these rules.

## Determinism

- **No browser automation.** No Selenium, Playwright, or client-side JS execution.
- **No inference.** Never guess country, board IDs, or job URLs.
- If job data is absent from the initial HTML or embedded JSON, fail cleanly and log the reason.
- Return empty results rather than partially-invalid jobs.
- Scraper-specific DOM/JSON extraction logic lives in the concrete scraper.

## Factory Pattern

- `AtsScraperFactory` selects a scraper via `supports(url)`, evaluated in order of specificity.
- `supports()` must be **conservative and narrowly scoped**.
- Each scraper needs positive AND negative `supports()` tests (e.g. an Ashby URL
  must not match Teamtailor).

## Embedded JSON Extraction

Some ATS platforms embed job data in inline `<script>` tags.

- Only extract JSON from **inline `<script>` tags**. Never parse external JS bundles.
- Prefer explicit JSON assignment markers (e.g. `VAR = {...};`).
- Regex extraction must terminate at the assignment boundary (`};`), not at arbitrary semicolons.
- If embedded data cannot be reliably extracted, log and return no jobs.

## Job URL Construction

- URLs must be **stable and deterministic**.
- If the ATS payload gives no URL, construct one only when the format is
  explicitly known (e.g. Ashby: `{career_page.url}/{job_id}`).
- If a URL cannot be constructed with certainty, **drop the job**.

## Type Narrowing

- `parse_job_card()` accepts `object` at the interface level.
- HTML scrapers narrow with `isinstance(card, bs4.Tag)`.
- JSON scrapers narrow with `isinstance(card, dict)`.
- Use runtime checks + `typing.cast`, not `Any` or `# type: ignore`.

## Location & Remote Detection

Location parsing, Europe filtering and remote detection live in the base
`AtsScraper` utilities (backed by `app/utils/locations/`). Never duplicate them per scraper.

## Logging

- Never hardcode the scraper class name in log messages. Use `cls.__name__` or
  `self.__class__.__name__`.
- Log reasons for skipping jobs (non-Europe, missing URL, JS-only boards).
