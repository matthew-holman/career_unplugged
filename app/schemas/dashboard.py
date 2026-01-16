from pydantic import BaseModel


class JobSummary(BaseModel):
    counts_by_source: dict[str, int]
    counts_by_country: dict[str, int]
    counts_by_remote_status: dict[str, int]
    to_review: int
    eu_remote: int
    sweden: int
    new7d: int
    positive_matches: int
