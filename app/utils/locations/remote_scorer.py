import re

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.job import Job


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


# The country the user applies from. A remote listing here is eligible by default.
_HOME_COUNTRY = "sweden"

# Maximum score for a remote job tied to a single country other than the home
# country, when nothing in the title or description widens its geography.
# Kept below the true_remote threshold (3): "remote in Germany" usually means
# you must live in Germany.
_RESTRICTED_COUNTRY_CAP = 2

# Regions that, when named alongside "remote", make a job open to the home country.
_ELIGIBLE_REGION = (
    r"(?:Europe|European\s+Union|EU|EEA|EMEA|Sweden|Nordics|Nordic\s+countries"
    r"|Scandinavia|worldwide|anywhere\s+in\s+the\s+world)"
)

# "anywhere", but not "anywhere up to 4 weeks" (workcation) or "anywhere in X"
# unless X is an eligible region. Patterns run with IGNORECASE, so the trailing
# [A-Z] matches any word: unlisted "anywhere in ..." phrases are rejected.
_ANYWHERE = (
    r"anywhere\b(?!\s+(?:up\s+to|for)\s+\d)"
    r"(?!\s+in\s+(?!(?:Europe|the\s+EU|EU|EMEA|EEA|the\s+world|Sweden|the\s+Nordics"
    r"|Scandinavia)\b)[A-Z])"
)

# Signals that a job's hiring geography extends beyond its listed country to
# include the home country. The "remote ... region" windows stay within one
# sentence so unrelated mentions elsewhere in the description don't count.
_SCOPE_PATTERNS = [
    # "remote ... Europe" / "Europe ... remote" within one sentence
    rf"\bremote\b[^.\n]{{0,40}}\b{_ELIGIBLE_REGION}\b",
    rf"\b{_ELIGIBLE_REGION}\b[^.\n]{{0,40}}\bremote\b",
    rf"\b(?:work|working|live|based)\s+(?:from\s+)?{_ANYWHERE}",
    r"\blocation[-\s]?agnostic\b",
    r"\b(?:Western[-\s])?European\s+time\s*zones?\b",
    r"\bacross\s+(?:EMEA|EU|Europe)\b",
]

# Region names in a title ("Engineering Manager, EMEA") widen geography on their own.
_TITLE_SCOPE_PATTERN = (
    r"\b(?:Europe|European|EU|EEA|EMEA|Sweden|Nordics?|Scandinavia|Worldwide)\b"
)


def _is_pan_european(country: str | None) -> bool:
    return country is not None and country.lower() in _REMOTE_LOCATION_COUNTRIES


def _is_home_country(country: str | None) -> bool:
    return country is not None and _HOME_COUNTRY in country.lower()


def _is_restricted_country(country: str | None) -> bool:
    """A specific country that is neither the home country nor a pan-EU region."""
    return (
        country is not None
        and country.strip() != ""
        and not _is_pan_european(country)
        and not _is_home_country(country)
    )


def _scope_signal(title: str, text: str) -> str | None:
    """Return the matched text if the job is explicitly open beyond one country."""
    if re.search(_TITLE_SCOPE_PATTERN, title, re.IGNORECASE):
        return f"region in title: {title}"
    for pattern in _SCOPE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return f'"{match.group(0)}"'
    return None


def _has_false_positive(text: str) -> bool:
    """Return True if the text contains a known false-positive remote phrase."""
    return any(re.search(fp, text, re.IGNORECASE) for fp in _FALSE_POSITIVE_PATTERNS)


def _first_pattern_match(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return pattern
    return None


def _score_from_location(job: "Job") -> tuple[int, str]:
    from app.job_scrapers.scraper import RemoteStatus

    country = job.country
    listing_remote = job.listing_remote

    if _is_pan_european(country):
        return 4, f"Pan-European/global location: {country}"

    if listing_remote == RemoteStatus.REMOTE:
        if _is_home_country(country):
            return 3, "Remote listing in Sweden"
        if country:
            # Remote within another country usually requires living there.
            return 2, f"Remote listing restricted to {country}"
        return 2, "Remote listing (country unknown)"

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
        2 — Hybrid listing, weak remote signals (timezone mentions, EoR/global
            payroll), or remote but restricted to a single non-Swedish country.
        1 — No meaningful remote signal.
        0 — Onsite listing with no contradicting signals.

    A job listed in a single country other than Sweden is capped at 2 unless its
    title or description explicitly names an eligible region (Europe, EU, EMEA,
    Sweden, Nordics, worldwide, anywhere). Working-style phrases such as
    "remote-first" or "fully remote" do not lift that cap on their own.
    """

    @staticmethod
    def score(job: "Job", description_text: str | None) -> tuple[int, str]:
        """
        Return (remote_score, reason_string).

        Uses job metadata (country, listing_remote, title) and the extracted
        description text. The highest confident signal wins; ONSITE listings
        and single-country listings without an eligible-region signal are
        capped at 2 even if description signals are stronger.
        """
        from app.job_scrapers.scraper import RemoteStatus

        text = description_text or ""
        location_score, location_reason = _score_from_location(job)
        title_score, title_reason = _score_from_title(job.title)
        desc_score, desc_reason = _score_from_description(text)

        best_score = max(location_score, title_score, desc_score)

        if best_score == desc_score and desc_reason:
            reason = desc_reason
        elif best_score == title_score and title_reason:
            reason = title_reason
        else:
            reason = location_reason

        if job.listing_remote == RemoteStatus.ONSITE:
            best_score = min(best_score, 2)

        if job.listing_remote == RemoteStatus.ONSITE or not _is_restricted_country(
            job.country
        ):
            return best_score, reason

        scope = _scope_signal(job.title, text)
        if scope is None:
            if best_score > _RESTRICTED_COUNTRY_CAP:
                return (
                    _RESTRICTED_COUNTRY_CAP,
                    f"Remote restricted to {job.country} ({reason})",
                )
            return best_score, reason

        # An explicit eligible region on a remote listing makes it eligible even
        # when no other description pattern scored above the cap.
        if job.listing_remote == RemoteStatus.REMOTE:
            if best_score <= _RESTRICTED_COUNTRY_CAP:
                reason = f"Remote listing in {job.country}"
            best_score = max(best_score, _RESTRICTED_COUNTRY_CAP + 1)
        if best_score > _RESTRICTED_COUNTRY_CAP:
            reason = f"{reason} (open beyond {job.country}: {scope})"
        return best_score, reason
