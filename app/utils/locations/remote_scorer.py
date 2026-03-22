import re

from typing import TYPE_CHECKING

from app.utils.locations.europe_filter import EuropeFilter

if TYPE_CHECKING:
    from app.models.job import Job
    from app.job_scrapers.scraper import RemoteStatus


# Patterns that indicate the company/role is structurally remote — score 5.
# These describe how the company operates, not a perk or allowance.
_PATTERNS_SCORE_5 = [
    r"\bremote[-\s]?first\b",
    r"\b100%[-\s]?remote\b",
    r"\bfully[-\s]?(remote|distributed)\b",
    r"\bfully[-\s]?distributed\b",
    r"\basync[-\s]?first\b",
    r"\bdistributed[-\s]?first\b",
    r"\bremote[-\s]?only\b",
]

# Patterns that indicate the role is explicitly open to remote workers from Europe — score 4.
_PATTERNS_SCORE_4 = [
    r"\bremote(?:ly)?\s+(?:within|from|across|in)\s+(?:Sweden|Europe|EU|EMEA|European\s+Union)\b",
    r"\bwork\s+(?:from\s+)?anywhere\s+(?:in|across|within)\s+(?:Europe|EU|EMEA)\b",
    r"\bwork\s+remotely\s+(?:from|in|within)\s+(?:Europe|EU|EMEA|Sweden)\b",
    r"\blocation[-\s]?agnostic\b",
    r"\bremote\s+in\s+eu\b",
    r"\bremote[-\s]?work\s+(?:within|across)\s+(?:Europe|EU|EMEA)\b",
    r"\bopen\s+to\s+(?:fully\s+)?remote\b",
    r"\bremote[-\s]?friendly\b",
    r"\bwork\s+from\s+anywhere\s+in\s+Europe\b",
]

# Patterns that give moderate confidence — score 3.
# These suggest remote-eligible hiring without explicitly confirming European scope.
_PATTERNS_SCORE_3 = [
    r"\bWestern[-\s]European\s+time\s*zones?\b",
    r"\bEuropean\s+time\s*zones?\b",
    r"\bflexible\s+location\b",
    r"\bno\s+relocation\s+(?:required|needed)\b",
    r"\bdistributed[-\s]?team\b",
    r"\bbased\s+in\s+(?:Europe|EU|EMEA)[\s,]+(?:but\s+)?open\s+to\s+remote\b",
    r"\bacross\s+(?:EMEA|EU|time\s*zones)\b",
]

# Patterns that are weak signals — score 2 from description alone.
# Timezone requirements suggest remote-compatible scheduling but not necessarily remote work.
_PATTERNS_SCORE_2 = [
    r"\b(?:GMT|CET|CEST|Central\s+European\s+(?:Standard\s+|Summer\s+)?Time)\b",
    r"\bUTC[\s±+\-]?\d{1,2}\b",
    r"\bEuropean\s+time\s*zone\b",
    r"\bwithin\s+\d{1,2}\s*h(?:rs?|ours?)?\s+of\s+(?:GMT|CET|UTC)\b",
    r"\btime[-\s]?zone:\s*(?:GMT|CET|UTC[\s+\-]?\d)\b",
    r"\bEmployer\s+of\s+Record\b",
    r"\bglobal\s+payroll\b",
]

# Patterns that look like remote signals but are frequently false positives.
# These are checked BEFORE scoring — a match here suppresses the candidate pattern.
_FALSE_POSITIVE_PATTERNS = [
    # "work from anywhere up to X weeks/days" — workcation policy, not remote work
    r"\bwork\s+from\s+anywhere\s+(?:up\s+to|for)\s+\d+\s+(?:weeks?|days?|months?)\b",
    # "work from anywhere in [single country]" — country-restricted, not EU-wide
    r"\bwork\s+from\s+anywhere\s+in\s+(?!Europe\b|EU\b|EMEA\b)[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?\b",
    # "X days/weeks working from home per year" — limited allowance
    r"\b\d+\s+(?:days?|weeks?)\s+(?:working\s+from\s+home|remote)\s+per\s+(?:year|month|week)\b",
    # "up to X days remote" — capped allowance
    r"\bup\s+to\s+\d+\s+days?\s+(?:per\s+(?:week|month))?\s*remote\b",
]

# Country values (on job.country) that indicate a pan-European or global posting — score 4.
_REMOTE_LOCATION_COUNTRIES = frozenset(
    c.lower()
    for c in [
        "EMEA",
        "European",
        "European Union",
        "European Economic Area",
        "Europe",
        "EU",
        "EEA",
        "Worldwide",
        "Global",
    ]
)


def _has_false_positive(text: str) -> bool:
    """Return True if the text contains a known false-positive remote phrase."""
    return any(
        re.search(fp, text, re.IGNORECASE) for fp in _FALSE_POSITIVE_PATTERNS
    )


def _first_pattern_match(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return pattern
    return None


def _score_from_location(job: "Job") -> tuple[int, str]:
    from app.job_scrapers.scraper import RemoteStatus

    country = job.country
    listing_remote = job.listing_remote

    if country and country.lower() in _REMOTE_LOCATION_COUNTRIES:
        return 4, f"Pan-European/global location: {country}"

    if listing_remote == RemoteStatus.REMOTE:
        if country and "sweden" in country.lower():
            return 3, "Remote listing in Sweden"
        if country and EuropeFilter.is_european(country):
            return 3, f"Remote listing in {country}"
        # Remote but unknown or non-European country — some signal but uncertain
        return 2, "Remote listing (non-European country)"

    if listing_remote == RemoteStatus.HYBRID:
        return 2, "Hybrid listing"

    if listing_remote == RemoteStatus.ONSITE:
        return 0, "Onsite listing"

    return 1, "No location remote signal"


def _score_from_title(title: str) -> tuple[int, str]:
    title_lower = title.lower()
    if re.search(r"\bremote\b", title_lower):
        return 3, f"Remote in title: {title}"
    if re.search(r"\b(emea|european?)\b", title_lower):
        return 2, f"Region in title: {title}"
    return 0, ""


def _score_from_description(text: str) -> tuple[int, str]:
    if not text:
        return 0, ""

    fp = _has_false_positive(text)

    match = _first_pattern_match(text, _PATTERNS_SCORE_5)
    if match:
        return 5, match

    match = _first_pattern_match(text, _PATTERNS_SCORE_4)
    if match and not fp:
        return 4, match

    match = _first_pattern_match(text, _PATTERNS_SCORE_3)
    if match and not fp:
        return 3, match

    match = _first_pattern_match(text, _PATTERNS_SCORE_2)
    if match:
        return 2, match

    return 0, ""


class RemoteScorer:
    """
    Score how remote-eligible a job is for someone working from Sweden/Europe.

    Score scale:
        5 — Explicitly remote-first / distributed / async-first company.
        4 — Role clearly open to remote workers from Europe/EU/EMEA.
        3 — Likely remote-eligible (Sweden remote, European timezone requirements, etc.)
        2 — Hybrid listing or weak remote signals (timezone mentions, EoR/global payroll).
        1 — No meaningful remote signal.
        0 — Onsite listing with no contradicting signals.
    """

    @staticmethod
    def score(job: "Job", description_text: str | None) -> tuple[int, str]:
        """
        Return (remote_score, reason_string).

        Uses job metadata (country, listing_remote, title) and the extracted
        description text. The highest confident signal wins; ONSITE listings
        are capped at 2 even if description signals are stronger.
        """
        location_score, location_reason = _score_from_location(job)
        title_score, title_reason = _score_from_title(job.title)
        desc_score, desc_reason = _score_from_description(description_text or "")

        best_score = max(location_score, title_score, desc_score)

        from app.job_scrapers.scraper import RemoteStatus

        if job.listing_remote == RemoteStatus.ONSITE:
            best_score = min(best_score, 2)

        if best_score == desc_score and desc_reason:
            reason = desc_reason
        elif best_score == title_score and title_reason:
            reason = title_reason
        else:
            reason = location_reason

        return best_score, reason
