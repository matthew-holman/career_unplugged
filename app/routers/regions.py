from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from app.utils.locations.europe_filter import EuropeFilter

router = APIRouter(prefix="/regions", tags=["Regions"])


class Region(BaseModel):
    key: str
    countries: List[str]


class RegionsResponse(BaseModel):
    regions: List[Region]


@router.get("", response_model=RegionsResponse)
def list_regions() -> RegionsResponse:
    eu_countries = sorted(EuropeFilter.EU_COUNTRIES)
    return RegionsResponse(regions=[Region(key="EU", countries=eu_countries)])
