from decimal import Decimal

from pydantic import BaseModel


class VendorSearchCriteria(BaseModel):
    trade: str
    location_lat: float | None = None
    location_lng: float | None = None
    radius_miles: int = 50
    min_rating: float = 0.0
    verified_only: bool = False


class VendorMatch(BaseModel):
    vendor_id: str
    company_name: str
    distance_miles: float
    rating: float
    trades: list[str]
    is_verified: bool
    match_score: float


class RFQPackage(BaseModel):
    project_title: str
    project_address: str | None
    scope_description: str
    required_trade: str
    estimated_start_date: str | None = None
    budget_range: str | None = None
    response_deadline_days: int = 7
