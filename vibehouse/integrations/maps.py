"""Mock maps / geocoding integration client.

Returns realistic fake geocoding results and nearby-vendor searches
without calling any external mapping API.
"""

from __future__ import annotations

import random
import uuid
from typing import Any

from vibehouse.integrations.base import BaseIntegration

# ---------------------------------------------------------------------------
# Pre-built mock data
# ---------------------------------------------------------------------------

_MOCK_ADDRESSES: list[dict[str, Any]] = [
    {
        "formatted_address": "742 Evergreen Terrace, Springfield, IL 62704, USA",
        "lat": 39.7817,
        "lng": -89.6501,
    },
    {
        "formatted_address": "1600 Pennsylvania Avenue NW, Washington, DC 20500, USA",
        "lat": 38.8977,
        "lng": -77.0365,
    },
    {
        "formatted_address": "350 Fifth Avenue, New York, NY 10118, USA",
        "lat": 40.7484,
        "lng": -73.9857,
    },
    {
        "formatted_address": "221 Baker Street, San Francisco, CA 94117, USA",
        "lat": 37.7749,
        "lng": -122.4194,
    },
    {
        "formatted_address": "456 Oak Lane, Austin, TX 78701, USA",
        "lat": 30.2672,
        "lng": -97.7431,
    },
]

_VENDOR_FIRST_NAMES: list[str] = [
    "Johnson's",
    "Elite",
    "Premier",
    "Heritage",
    "Summit",
    "Blue Ridge",
    "Capital",
    "Precision",
    "Craftsman",
    "All-Pro",
    "Valley",
    "Pinnacle",
    "Cornerstone",
    "Lakeside",
    "Greenfield",
]

_TRADE_SUFFIXES: dict[str, list[str]] = {
    "plumbing": ["Plumbing", "Plumbing & Heating", "Pipe Works"],
    "electrical": ["Electric", "Electrical Services", "Power Solutions"],
    "painting": ["Painting", "Painting & Coatings", "Paint Pros"],
    "flooring": ["Flooring", "Floor Design", "Hardwood Specialists"],
    "roofing": ["Roofing", "Roofing & Exteriors", "Roof Masters"],
    "hvac": ["HVAC", "Climate Control", "Heating & Air"],
    "general": ["Construction", "Home Services", "Renovations", "Contracting"],
    "tile": ["Tile & Stone", "Tile Works", "Tile Installation"],
    "cabinetry": ["Cabinetry", "Custom Cabinets", "Woodworks"],
    "landscaping": ["Landscaping", "Lawn & Garden", "Outdoor Living"],
}


def _vendor_name(trade: str) -> str:
    """Generate a plausible vendor business name for the given trade."""
    first = random.choice(_VENDOR_FIRST_NAMES)
    suffixes = _TRADE_SUFFIXES.get(trade.lower(), _TRADE_SUFFIXES["general"])
    suffix = random.choice(suffixes)
    return f"{first} {suffix}"


class MapsClient(BaseIntegration):
    """Mock maps / geocoding client returning realistic fake data."""

    def __init__(self) -> None:
        super().__init__("maps")

    async def health_check(self) -> bool:
        self.logger.info("Maps client health check: OK (mock)")
        return True

    # ------------------------------------------------------------------
    # Geocoding
    # ------------------------------------------------------------------

    async def geocode_address(self, address: str) -> dict[str, Any]:
        """Geocode a free-form address string into lat/lng coordinates.

        Returns a dict with ``lat``, ``lng``, and ``formatted_address``
        fields.  The mock implementation picks a realistic US location
        seeded from the input so the same address always returns the
        same result.
        """
        self.logger.info("Geocoding address: '%s'", address)

        # Deterministic-ish selection based on input length so the same
        # address always resolves to the same mock location.
        idx = len(address) % len(_MOCK_ADDRESSES)
        base = _MOCK_ADDRESSES[idx]

        # Small jitter so near-duplicate addresses get slightly different
        # coordinates (keeps downstream distance maths interesting).
        jitter_lat = (hash(address) % 1000) / 100_000
        jitter_lng = (hash(address[::-1]) % 1000) / 100_000

        result: dict[str, Any] = {
            "lat": round(base["lat"] + jitter_lat, 6),
            "lng": round(base["lng"] + jitter_lng, 6),
            "formatted_address": base["formatted_address"],
            "place_id": uuid.uuid4().hex[:24],
            "input_address": address,
            "confidence": round(random.uniform(0.88, 0.99), 2),
        }

        self.logger.info(
            "Geocoded '%s' -> (%.6f, %.6f) [%s]",
            address,
            result["lat"],
            result["lng"],
            result["formatted_address"],
        )
        return result

    # ------------------------------------------------------------------
    # Nearby vendor search
    # ------------------------------------------------------------------

    async def find_nearby_vendors(
        self,
        lat: float,
        lng: float,
        radius_miles: float = 25.0,
        trade: str = "general",
    ) -> list[dict[str, Any]]:
        """Find vendors near a given coordinate within *radius_miles*.

        Returns a list of 5-10 mock vendor result dicts, each containing
        ``name``, ``distance_miles``, ``rating``, ``review_count``,
        ``phone``, ``address``, and ``trade`` fields.
        """
        self.logger.info(
            "Searching nearby vendors: lat=%.6f lng=%.6f radius=%.1f mi trade=%s",
            lat,
            lng,
            radius_miles,
            trade,
        )

        count = random.randint(5, 10)
        vendors: list[dict[str, Any]] = []

        # Use a set to avoid duplicate names within a single result set.
        used_names: set[str] = set()

        for _ in range(count):
            name = _vendor_name(trade)
            while name in used_names:
                name = _vendor_name(trade)
            used_names.add(name)

            distance = round(random.uniform(0.5, radius_miles), 1)
            rating = round(random.uniform(3.5, 5.0), 1)
            review_count = random.randint(8, 480)
            area_code = random.choice(["512", "737", "310", "718", "202", "312", "415"])
            phone = f"+1{area_code}{random.randint(2000000, 9999999)}"
            street_num = random.randint(100, 9999)
            street_name = random.choice(
                [
                    "Main St",
                    "Commerce Dr",
                    "Industrial Blvd",
                    "Elm Ave",
                    "Oak Rd",
                    "Maple Ln",
                    "Cedar Way",
                    "Park Ave",
                    "Market St",
                    "Washington Blvd",
                ]
            )

            vendors.append(
                {
                    "id": uuid.uuid4().hex[:16],
                    "name": name,
                    "trade": trade,
                    "distance_miles": distance,
                    "rating": rating,
                    "review_count": review_count,
                    "phone": phone,
                    "address": f"{street_num} {street_name}",
                    "licensed": random.choice([True, True, True, False]),
                    "insured": True,
                    "years_in_business": random.randint(2, 35),
                    "lat": round(lat + random.uniform(-0.1, 0.1), 6),
                    "lng": round(lng + random.uniform(-0.1, 0.1), 6),
                }
            )

        # Sort by distance so nearest vendors appear first.
        vendors.sort(key=lambda v: v["distance_miles"])

        self.logger.info(
            "Found %d mock vendors for trade '%s' within %.1f mi",
            len(vendors),
            trade,
            radius_miles,
        )
        return vendors
