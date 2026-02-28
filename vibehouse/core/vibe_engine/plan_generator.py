"""Floor-plan generator for the Vibe Engine.

Takes a validated ``RequirementSpecification`` (RSO) and produces three
``DesignOption`` variants:

- **Option A – Efficient Living**: budget-optimised, compact layout.
- **Option B – Spacious Comfort**: balanced cost / space trade-off.
- **Option C – Premium Design**: maximum space and luxury features.

This is a deterministic mock implementation.  A production version would
call into a generative-AI floor-plan model.
"""

from __future__ import annotations

import math
import uuid

from vibehouse.core.vibe_engine.schemas import (
    DesignOption,
    RequirementSpecification,
    RoomLayout,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Base cost per square foot by style (rough national averages, 2024 USD).
_COST_PER_SQFT: dict[str, float] = {
    "modern": 195.0,
    "contemporary": 200.0,
    "farmhouse": 175.0,
    "craftsman": 185.0,
    "colonial": 180.0,
    "ranch": 160.0,
}


def _cost_per_sqft(style: str) -> float:
    return _COST_PER_SQFT.get(style, 185.0)


def _build_rooms(
    rso: RequirementSpecification,
    sqft_multiplier: float,
) -> list[RoomLayout]:
    """Generate a realistic room list scaled by *sqft_multiplier*.

    ``sqft_multiplier`` controls how generous each room is relative to
    minimums:

    - 0.85  -> compact / efficient
    - 1.00  -> standard / balanced
    - 1.20  -> premium / spacious
    """
    rooms: list[RoomLayout] = []

    # ── Bedrooms ─────────────────────────────────────────────────────
    primary_sqft = int(220 * sqft_multiplier)
    rooms.append(RoomLayout(room_name="Primary Bedroom", sqft=primary_sqft, floor=rso.floors))

    for i in range(1, rso.bedrooms):
        sqft = int(150 * sqft_multiplier)
        # Put extra bedrooms on the top floor for multi-storey plans
        floor = min(i + 1, rso.floors) if rso.floors > 1 else 1
        rooms.append(RoomLayout(room_name=f"Bedroom {i + 1}", sqft=sqft, floor=floor))

    # ── Bathrooms ────────────────────────────────────────────────────
    full_baths = int(rso.bathrooms)
    half_baths = 1 if rso.bathrooms % 1 >= 0.5 else 0

    rooms.append(
        RoomLayout(
            room_name="Primary Bathroom",
            sqft=int(100 * sqft_multiplier),
            floor=rso.floors,
        )
    )
    for i in range(1, full_baths):
        rooms.append(
            RoomLayout(
                room_name=f"Bathroom {i + 1}",
                sqft=int(65 * sqft_multiplier),
                floor=max(1, rso.floors - i + 1) if rso.floors > 1 else 1,
            )
        )
    for _ in range(half_baths):
        rooms.append(
            RoomLayout(room_name="Half Bath", sqft=int(35 * sqft_multiplier), floor=1)
        )

    # ── Common living areas (always on floor 1) ─────────────────────
    rooms.append(
        RoomLayout(room_name="Kitchen", sqft=int(200 * sqft_multiplier), floor=1)
    )
    rooms.append(
        RoomLayout(room_name="Living Room", sqft=int(280 * sqft_multiplier), floor=1)
    )
    rooms.append(
        RoomLayout(room_name="Dining Room", sqft=int(160 * sqft_multiplier), floor=1)
    )
    rooms.append(
        RoomLayout(room_name="Laundry Room", sqft=int(60 * sqft_multiplier), floor=1)
    )
    rooms.append(
        RoomLayout(room_name="Foyer / Entry", sqft=int(50 * sqft_multiplier), floor=1)
    )

    # ── Optional spaces ─────────────────────────────────────────────
    if rso.garage:
        # Garage is unconditioned, but included for layout purposes
        rooms.append(
            RoomLayout(room_name="Garage", sqft=int(440 * sqft_multiplier), floor=1)
        )

    if rso.outdoor_space:
        rooms.append(
            RoomLayout(
                room_name="Covered Patio / Outdoor Living",
                sqft=int(200 * sqft_multiplier),
                floor=1,
            )
        )

    # ── Special requirements ────────────────────────────────────────
    for req in rso.special_requirements:
        rooms.append(
            RoomLayout(
                room_name=req,
                sqft=int(120 * sqft_multiplier),
                floor=1 if rso.floors == 1 else rso.floors,
            )
        )

    # ── Hallways & Circulation (rough estimate) ─────────────────────
    conditioned_sqft = sum(r.sqft for r in rooms if r.room_name != "Garage")
    circulation = int(conditioned_sqft * 0.08)
    rooms.append(
        RoomLayout(room_name="Hallways / Circulation", sqft=circulation, floor=1)
    )

    return rooms


def _total_living_sqft(rooms: list[RoomLayout]) -> int:
    """Sum of all room areas excluding the garage."""
    return sum(r.sqft for r in rooms if r.room_name != "Garage")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_plans(rso: RequirementSpecification) -> list[DesignOption]:
    """Generate three floor-plan options from a requirement specification.

    Parameters
    ----------
    rso:
        The parsed and validated ``RequirementSpecification`` (RSO).

    Returns
    -------
    list[DesignOption]
        Three design options ranked from budget-friendly to premium.
    """
    cost_sqft = _cost_per_sqft(rso.style)
    options: list[DesignOption] = []

    # ── Option A: Efficient Living ──────────────────────────────────
    rooms_a = _build_rooms(rso, sqft_multiplier=0.85)
    total_a = _total_living_sqft(rooms_a)
    cost_a = int(total_a * cost_sqft * 0.90)  # 10 % efficiency savings
    options.append(
        DesignOption(
            option_id=f"opt_{uuid.uuid4().hex[:8]}",
            title="Efficient Living",
            description=(
                "A compact, budget-conscious design that maximises every square foot. "
                "Open-concept living and dining areas keep the footprint tight without "
                "sacrificing liveability.  Ideal for cost-sensitive builds."
            ),
            total_sqft=total_a,
            rooms=rooms_a,
            estimated_cost=cost_a,
            style_score=round(7.5 + (0.3 if rso.style == "ranch" else 0.0), 1),
            efficiency_score=9.2,
            floor_plan_url=None,
        )
    )

    # ── Option B: Spacious Comfort ──────────────────────────────────
    rooms_b = _build_rooms(rso, sqft_multiplier=1.00)
    total_b = _total_living_sqft(rooms_b)
    cost_b = int(total_b * cost_sqft)
    options.append(
        DesignOption(
            option_id=f"opt_{uuid.uuid4().hex[:8]}",
            title="Spacious Comfort",
            description=(
                "A well-balanced design offering comfortable room sizes and thoughtful "
                "flow between spaces.  The kitchen opens to both the dining and living "
                "areas, with generous bedrooms and ample storage."
            ),
            total_sqft=total_b,
            rooms=rooms_b,
            estimated_cost=cost_b,
            style_score=8.5,
            efficiency_score=7.8,
            floor_plan_url=None,
        )
    )

    # ── Option C: Premium Design ────────────────────────────────────
    rooms_c = _build_rooms(rso, sqft_multiplier=1.20)
    total_c = _total_living_sqft(rooms_c)
    cost_c = int(total_c * cost_sqft * 1.12)  # 12 % premium finishes
    options.append(
        DesignOption(
            option_id=f"opt_{uuid.uuid4().hex[:8]}",
            title="Premium Design",
            description=(
                "A spacious, high-end design with oversized rooms, luxury finishes, "
                "and room to grow.  Features a grand entry foyer, spa-inspired primary "
                "bath, and chef's kitchen with island seating."
            ),
            total_sqft=total_c,
            rooms=rooms_c,
            estimated_cost=cost_c,
            style_score=9.4,
            efficiency_score=6.5,
            floor_plan_url=None,
        )
    )

    return options
