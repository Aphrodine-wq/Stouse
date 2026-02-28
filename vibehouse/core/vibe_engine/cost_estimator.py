"""Cost estimation engine for the Vibe Engine.

Produces an itemised ``CostEstimate`` (materials + labour + contingency)
for a given ``DesignOption``.  Costs are derived from per-square-foot
national averages scaled to the design's total living area.

A production version would integrate with RSMeans, BuildZoom, or a
real-time materials-pricing API.
"""

from __future__ import annotations

import math

from vibehouse.core.vibe_engine.schemas import (
    CostEstimate,
    DesignOption,
    MaterialItem,
)


# ---------------------------------------------------------------------------
# Regional cost multipliers (stub — always 1.0 for now)
# ---------------------------------------------------------------------------

_LOCATION_MULTIPLIERS: dict[str, float] = {
    "san francisco": 1.35,
    "new york": 1.30,
    "los angeles": 1.25,
    "seattle": 1.20,
    "denver": 1.10,
    "austin": 1.05,
    "dallas": 1.00,
    "atlanta": 0.95,
    "phoenix": 0.95,
    "houston": 0.95,
    "chicago": 1.10,
    "miami": 1.05,
}


def _location_multiplier(location: str | None) -> float:
    if not location:
        return 1.0
    key = location.strip().lower()
    # Try exact match, then partial
    if key in _LOCATION_MULTIPLIERS:
        return _LOCATION_MULTIPLIERS[key]
    for city, mult in _LOCATION_MULTIPLIERS.items():
        if city in key or key in city:
            return mult
    return 1.0


# ---------------------------------------------------------------------------
# Material take-off helpers
# ---------------------------------------------------------------------------


def _concrete_items(sqft: float, floors: int, mult: float) -> list[MaterialItem]:
    """Foundation and flatwork concrete."""
    # Foundation slab: ~0.012 cu yd per sqft of footprint
    footprint = sqft / max(floors, 1)
    slab_cuyd = round(footprint * 0.012, 1)
    slab_cost = round(185.0 * mult, 2)

    items = [
        MaterialItem(
            name="Foundation Concrete (4000 PSI)",
            category="Concrete",
            quantity=slab_cuyd,
            unit="cu yd",
            unit_cost=slab_cost,
            total_cost=round(slab_cuyd * slab_cost, 2),
        ),
    ]

    # Footings
    footing_cuyd = round(footprint * 0.006, 1)
    items.append(
        MaterialItem(
            name="Footing Concrete (3500 PSI)",
            category="Concrete",
            quantity=footing_cuyd,
            unit="cu yd",
            unit_cost=round(175.0 * mult, 2),
            total_cost=round(footing_cuyd * 175.0 * mult, 2),
        )
    )

    # Rebar
    rebar_lbs = round(footprint * 1.2, 0)
    items.append(
        MaterialItem(
            name="Rebar (#4 & #5 Grade 60)",
            category="Concrete",
            quantity=rebar_lbs,
            unit="lbs",
            unit_cost=round(0.75 * mult, 2),
            total_cost=round(rebar_lbs * 0.75 * mult, 2),
        )
    )

    return items


def _lumber_items(sqft: float, floors: int, mult: float) -> list[MaterialItem]:
    """Framing lumber and sheathing."""
    # Rough rule: ~6.5 board feet per sqft of living space
    bd_ft = round(sqft * 6.5, 0)
    items = [
        MaterialItem(
            name="Framing Lumber (SPF #2, 2x6)",
            category="Lumber",
            quantity=bd_ft,
            unit="bd ft",
            unit_cost=round(0.85 * mult, 2),
            total_cost=round(bd_ft * 0.85 * mult, 2),
        ),
    ]

    # Sheathing: ~1 sheet per 32 sqft of wall + floor area
    wall_area = math.sqrt(sqft / max(floors, 1)) * 4 * 9 * floors  # perimeter * height
    floor_area = sqft
    sheets = math.ceil((wall_area + floor_area) / 32)
    items.append(
        MaterialItem(
            name='OSB Sheathing (7/16")',
            category="Lumber",
            quantity=sheets,
            unit="sheets (4x8)",
            unit_cost=round(28.0 * mult, 2),
            total_cost=round(sheets * 28.0 * mult, 2),
        )
    )

    # Engineered I-joists for floors > 1
    if floors > 1:
        joist_count = math.ceil(sqft / max(floors, 1) / 1.33)  # 16" O.C.
        items.append(
            MaterialItem(
                name="Engineered I-Joists (TJI 210, 11-7/8\")",
                category="Lumber",
                quantity=joist_count,
                unit="ea",
                unit_cost=round(18.50 * mult, 2),
                total_cost=round(joist_count * 18.50 * mult, 2),
            )
        )

    return items


def _roofing_items(sqft: float, floors: int, mult: float) -> list[MaterialItem]:
    """Roofing materials."""
    # Roof area ≈ footprint * 1.15 (pitch factor) in "squares" (100 sqft)
    footprint = sqft / max(floors, 1)
    roof_sqft = footprint * 1.15
    squares = round(roof_sqft / 100, 1)

    return [
        MaterialItem(
            name="Architectural Shingles (30-year)",
            category="Roofing",
            quantity=squares,
            unit="sq (100 sqft)",
            unit_cost=round(120.0 * mult, 2),
            total_cost=round(squares * 120.0 * mult, 2),
        ),
        MaterialItem(
            name="Roofing Underlayment (synthetic)",
            category="Roofing",
            quantity=squares,
            unit="sq",
            unit_cost=round(25.0 * mult, 2),
            total_cost=round(squares * 25.0 * mult, 2),
        ),
        MaterialItem(
            name="Drip Edge & Flashing",
            category="Roofing",
            quantity=round(math.sqrt(footprint) * 4, 0),
            unit="lin ft",
            unit_cost=round(2.50 * mult, 2),
            total_cost=round(math.sqrt(footprint) * 4 * 2.50 * mult, 2),
        ),
    ]


def _insulation_items(sqft: float, floors: int, mult: float) -> list[MaterialItem]:
    """Insulation materials."""
    wall_sqft = math.sqrt(sqft / max(floors, 1)) * 4 * 9 * floors
    return [
        MaterialItem(
            name='Batt Insulation (R-21, 2x6 walls)',
            category="Insulation",
            quantity=round(wall_sqft, 0),
            unit="sq ft",
            unit_cost=round(1.10 * mult, 2),
            total_cost=round(wall_sqft * 1.10 * mult, 2),
        ),
        MaterialItem(
            name="Blown-in Attic Insulation (R-49)",
            category="Insulation",
            quantity=round(sqft / max(floors, 1), 0),
            unit="sq ft",
            unit_cost=round(1.75 * mult, 2),
            total_cost=round(sqft / max(floors, 1) * 1.75 * mult, 2),
        ),
    ]


def _electrical_items(sqft: float, mult: float) -> list[MaterialItem]:
    """Electrical rough materials."""
    wire_ft = round(sqft * 3.5, 0)  # ~3.5 ft of wire per sqft
    outlets = max(12, math.ceil(sqft / 80))
    return [
        MaterialItem(
            name="Romex NM-B 14/2 Wire",
            category="Electrical",
            quantity=wire_ft,
            unit="ft",
            unit_cost=round(0.45 * mult, 2),
            total_cost=round(wire_ft * 0.45 * mult, 2),
        ),
        MaterialItem(
            name="Electrical Panel (200A)",
            category="Electrical",
            quantity=1,
            unit="ea",
            unit_cost=round(1_800.0 * mult, 2),
            total_cost=round(1_800.0 * mult, 2),
        ),
        MaterialItem(
            name="Outlets / Switches / Covers",
            category="Electrical",
            quantity=outlets,
            unit="ea",
            unit_cost=round(12.0 * mult, 2),
            total_cost=round(outlets * 12.0 * mult, 2),
        ),
    ]


def _plumbing_items(sqft: float, bathrooms: int, mult: float) -> list[MaterialItem]:
    """Plumbing rough materials."""
    pipe_ft = round(sqft * 1.2, 0)
    return [
        MaterialItem(
            name='PEX Tubing (3/4" & 1/2")',
            category="Plumbing",
            quantity=pipe_ft,
            unit="ft",
            unit_cost=round(1.25 * mult, 2),
            total_cost=round(pipe_ft * 1.25 * mult, 2),
        ),
        MaterialItem(
            name='PVC Drain Pipe (3" & 4")',
            category="Plumbing",
            quantity=round(pipe_ft * 0.4, 0),
            unit="ft",
            unit_cost=round(3.50 * mult, 2),
            total_cost=round(pipe_ft * 0.4 * 3.50 * mult, 2),
        ),
        MaterialItem(
            name="Water Heater (50 gal, gas)",
            category="Plumbing",
            quantity=max(1, math.ceil(bathrooms / 3)),
            unit="ea",
            unit_cost=round(1_400.0 * mult, 2),
            total_cost=round(max(1, math.ceil(bathrooms / 3)) * 1_400.0 * mult, 2),
        ),
    ]


def _hvac_items(sqft: float, mult: float) -> list[MaterialItem]:
    """HVAC equipment and ductwork."""
    tonnage = round(max(1.5, sqft / 550), 1)
    duct_ft = round(sqft * 0.8, 0)
    return [
        MaterialItem(
            name=f"HVAC System ({tonnage}-ton split system)",
            category="HVAC",
            quantity=1,
            unit="ea",
            unit_cost=round(tonnage * 3_200.0 * mult, 2),
            total_cost=round(tonnage * 3_200.0 * mult, 2),
        ),
        MaterialItem(
            name="Ductwork (flex & rigid)",
            category="HVAC",
            quantity=duct_ft,
            unit="ft",
            unit_cost=round(6.50 * mult, 2),
            total_cost=round(duct_ft * 6.50 * mult, 2),
        ),
    ]


def _drywall_items(sqft: float, floors: int, mult: float) -> list[MaterialItem]:
    """Drywall / interior finishing."""
    # Wall area + ceilings
    wall_sqft = math.sqrt(sqft / max(floors, 1)) * 4 * 9 * floors
    ceiling_sqft = sqft  # roughly equals floor area
    total_dw = wall_sqft + ceiling_sqft
    sheets = math.ceil(total_dw / 32)  # 4x8 sheets
    return [
        MaterialItem(
            name='Drywall (1/2" 4x8 sheets)',
            category="Interior",
            quantity=sheets,
            unit="sheets",
            unit_cost=round(14.50 * mult, 2),
            total_cost=round(sheets * 14.50 * mult, 2),
        ),
        MaterialItem(
            name="Joint Compound & Tape",
            category="Interior",
            quantity=math.ceil(sheets / 10),
            unit="buckets",
            unit_cost=round(18.00 * mult, 2),
            total_cost=round(math.ceil(sheets / 10) * 18.00 * mult, 2),
        ),
    ]


# ---------------------------------------------------------------------------
# Labour cost helpers
# ---------------------------------------------------------------------------

def _labor_costs(sqft: float, floors: int, mult: float) -> dict[str, float]:
    """Estimate labour costs by trade."""
    return {
        "Site Work & Excavation": round(sqft * 3.50 * mult, 2),
        "Concrete & Foundation": round(sqft * 5.00 * mult, 2),
        "Framing": round(sqft * 12.00 * mult * (1.0 + 0.15 * (floors - 1)), 2),
        "Roofing": round(sqft / max(floors, 1) * 4.50 * mult, 2),
        "Plumbing": round(sqft * 5.50 * mult, 2),
        "Electrical": round(sqft * 5.00 * mult, 2),
        "HVAC": round(sqft * 4.50 * mult, 2),
        "Insulation": round(sqft * 2.00 * mult, 2),
        "Drywall": round(sqft * 3.50 * mult, 2),
        "Painting": round(sqft * 3.00 * mult, 2),
        "Flooring": round(sqft * 6.00 * mult, 2),
        "Cabinetry & Countertops": round(sqft * 4.00 * mult, 2),
        "Trim & Finish Carpentry": round(sqft * 3.50 * mult, 2),
        "Windows & Doors": round(sqft * 3.00 * mult, 2),
        "Exterior Finishes (Siding)": round(sqft * 3.50 * mult, 2),
        "Cleanup & Dumpsters": round(sqft * 1.00 * mult, 2),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def estimate_costs(
    design: DesignOption,
    location: str | None = None,
) -> CostEstimate:
    """Produce an itemised cost estimate for *design*.

    Parameters
    ----------
    design:
        A ``DesignOption`` from the plan generator.
    location:
        Optional city / region name used to apply a cost multiplier.

    Returns
    -------
    CostEstimate
        Full cost breakdown: materials, labour, contingency, and grand total.
    """
    sqft = design.total_sqft
    floors = max(r.floor for r in design.rooms) if design.rooms else 1
    mult = _location_multiplier(location)

    # Count bathrooms from rooms list
    bathroom_count = sum(1 for r in design.rooms if "bath" in r.room_name.lower())

    # ── Gather all material items ───────────────────────────────────
    materials: list[MaterialItem] = []
    materials.extend(_concrete_items(sqft, floors, mult))
    materials.extend(_lumber_items(sqft, floors, mult))
    materials.extend(_roofing_items(sqft, floors, mult))
    materials.extend(_insulation_items(sqft, floors, mult))
    materials.extend(_electrical_items(sqft, mult))
    materials.extend(_plumbing_items(sqft, bathroom_count, mult))
    materials.extend(_hvac_items(sqft, mult))
    materials.extend(_drywall_items(sqft, floors, mult))

    total_materials = round(sum(m.total_cost for m in materials), 2)

    # ── Labour ──────────────────────────────────────────────────────
    labor = _labor_costs(sqft, floors, mult)
    total_labor = round(sum(labor.values()), 2)

    # ── Contingency & grand total ───────────────────────────────────
    subtotal = total_materials + total_labor
    contingency = round(subtotal * 0.10, 2)
    grand_total = round(subtotal + contingency, 2)

    return CostEstimate(
        materials=materials,
        labor_costs=labor,
        total_materials=total_materials,
        total_labor=total_labor,
        contingency=contingency,
        grand_total=grand_total,
    )
