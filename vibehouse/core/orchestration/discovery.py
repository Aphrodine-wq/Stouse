import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.common.logging import get_logger
from vibehouse.core.orchestration.schemas import VendorMatch, VendorSearchCriteria
from vibehouse.db.models.vendor import Vendor

logger = get_logger("orchestration.discovery")


def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 3959  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _calculate_match_score(vendor: Vendor, distance: float, trade: str) -> float:
    score = 0.0

    # Rating component (0-40 points)
    score += (vendor.rating / 5.0) * 40

    # Distance component (0-30 points, closer is better)
    if distance <= 10:
        score += 30
    elif distance <= 25:
        score += 20
    elif distance <= 50:
        score += 10

    # Verification bonus (0-15 points)
    if vendor.is_verified:
        score += 15

    # Experience bonus (0-15 points)
    if vendor.total_projects >= 20:
        score += 15
    elif vendor.total_projects >= 10:
        score += 10
    elif vendor.total_projects >= 5:
        score += 5

    return round(score, 1)


async def discover_vendors(
    criteria: VendorSearchCriteria, db: AsyncSession
) -> list[VendorMatch]:
    logger.info("Discovering vendors for trade: %s", criteria.trade)

    query = select(Vendor).where(Vendor.is_deleted.is_(False))

    if criteria.verified_only:
        query = query.where(Vendor.is_verified.is_(True))
    if criteria.min_rating > 0:
        query = query.where(Vendor.rating >= criteria.min_rating)

    result = await db.execute(query)
    all_vendors = result.scalars().all()

    matches = []
    for vendor in all_vendors:
        # Check trade match
        vendor_trades = vendor.trades or []
        if not any(criteria.trade.lower() in t.lower() for t in vendor_trades):
            continue

        # Calculate distance if coordinates available
        distance = 0.0
        if criteria.location_lat and criteria.location_lng and vendor.location_lat and vendor.location_lng:
            distance = _haversine_distance(
                criteria.location_lat, criteria.location_lng,
                vendor.location_lat, vendor.location_lng,
            )
            if distance > criteria.radius_miles:
                continue

        match_score = _calculate_match_score(vendor, distance, criteria.trade)

        matches.append(
            VendorMatch(
                vendor_id=str(vendor.id),
                company_name=vendor.company_name,
                distance_miles=round(distance, 1),
                rating=vendor.rating,
                trades=vendor_trades,
                is_verified=vendor.is_verified,
                match_score=match_score,
            )
        )

    # Sort by match score descending
    matches.sort(key=lambda m: m.match_score, reverse=True)

    logger.info("Found %d vendor matches for trade: %s", len(matches), criteria.trade)
    return matches
