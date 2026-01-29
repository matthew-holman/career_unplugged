from datetime import datetime

from pydantic import BaseModel


class CareerPageFilter(BaseModel):
    company_name: str | None = None
    url: str | None = None
    active: bool | None = None
    last_synced_at_gte: datetime | None = None
    last_synced_at_lte: datetime | None = None
    deactivated_at_gte: datetime | None = None
    deactivated_at_lte: datetime | None = None
    last_status_code: int | None = None
