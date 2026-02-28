"""Structural and MEP analysis for the Vibe Engine.

Provides two mock analysis functions that produce realistic-looking
engineering data derived from a ``DesignOption``.  A production version
would call into structural-engineering calculation software (e.g. RISA,
SAP2000) and MEP sizing tools.
"""

from __future__ import annotations

import math

from vibehouse.core.vibe_engine.schemas import (
    DesignOption,
    EngineeringReport,
    MEPPlan,
)


# ---------------------------------------------------------------------------
# Foundation selection heuristics
# ---------------------------------------------------------------------------

def _select_foundation(design: DesignOption) -> str:
    """Choose a foundation type based on total sqft and floor count."""
    floors = max(r.floor for r in design.rooms) if design.rooms else 1
    if floors >= 3 or design.total_sqft > 4_000:
        return "full basement"
    if floors == 2 or design.total_sqft > 2_500:
        return "crawl space"
    return "slab-on-grade"


def _select_structural_system(design: DesignOption) -> str:
    """Choose a structural system based on size."""
    if design.total_sqft > 5_000:
        return "steel frame with wood infill"
    if design.total_sqft > 3_500:
        return "engineered wood frame (LVL/TJI)"
    return "conventional wood frame (2x6)"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_structure(design: DesignOption) -> EngineeringReport:
    """Perform a mock structural analysis for *design*.

    Parameters
    ----------
    design:
        A ``DesignOption`` produced by the plan generator.

    Returns
    -------
    EngineeringReport
        Structural specifications, load calculations, material specs,
        and code-compliance notes.
    """
    sqft = design.total_sqft
    floors = max(r.floor for r in design.rooms) if design.rooms else 1
    foundation = _select_foundation(design)
    structural_system = _select_structural_system(design)

    # ── Load calculations (simplified per IRC/IBC) ──────────────────
    dead_load_floor_psf = 15.0  # typical wood-frame floor dead load
    live_load_floor_psf = 40.0  # residential live load per IBC
    dead_load_roof_psf = 12.0
    live_load_roof_psf = 20.0   # non-snow region default
    wind_load_psf = 25.0        # moderate wind zone

    # Total gravity load on foundation (rough)
    total_gravity_kips = round(
        (dead_load_floor_psf + live_load_floor_psf) * sqft * floors / 1_000
        + (dead_load_roof_psf + live_load_roof_psf) * (sqft / max(floors, 1)) / 1_000,
        1,
    )

    # Bearing wall linear load (assume perimeter ~ sqrt of footprint)
    perimeter_ft = 4 * math.sqrt(sqft / max(floors, 1))
    bearing_wall_plf = round(total_gravity_kips * 1_000 / perimeter_ft, 0)

    load_calculations: dict[str, float] = {
        "dead_load_floor_psf": dead_load_floor_psf,
        "live_load_floor_psf": live_load_floor_psf,
        "dead_load_roof_psf": dead_load_roof_psf,
        "live_load_roof_psf": live_load_roof_psf,
        "wind_load_psf": wind_load_psf,
        "total_gravity_kips": total_gravity_kips,
        "bearing_wall_plf": bearing_wall_plf,
    }

    # ── Material specifications ─────────────────────────────────────
    material_specs: dict[str, str] = {
        "foundation_concrete": "4000 PSI normal-weight concrete",
        "rebar": "#4 and #5 Grade 60 rebar",
        "framing_lumber": "SPF #2 or better, kiln-dried",
        "sheathing": '7/16" OSB structural sheathing',
        "fasteners": "16d common nails per IRC Table R602.3(1)",
    }

    if "steel" in structural_system.lower():
        material_specs["steel_beams"] = "W10x22 A992 Grade 50 wide-flange"
        material_specs["steel_columns"] = 'HSS 4x4x1/4" A500 Grade B'

    if "engineered" in structural_system.lower():
        material_specs["lvl_beams"] = '1-3/4" x 11-7/8" LVL (2.0E)'
        material_specs["tji_joists"] = 'TJI 210 at 16" O.C.'

    if foundation == "full basement":
        material_specs["basement_walls"] = '10" poured concrete or 12" CMU'

    # ── Compliance notes ────────────────────────────────────────────
    compliance_notes: list[str] = [
        "Design complies with IRC 2021 for one- and two-family dwellings.",
        f"Foundation type: {foundation} — verify local frost-depth requirements.",
        f"Roof framing designed for {live_load_roof_psf} PSF live load; "
        "verify local snow-load requirements and adjust if necessary.",
        "Lateral bracing per IRC Section R602.10 (wall bracing).",
        "All structural connections to use Simpson Strong-Tie or equivalent hardware.",
    ]

    if floors >= 2:
        compliance_notes.append(
            "Second-floor framing requires engineered joist schedule — "
            "refer to TJI span tables for final sizing."
        )

    if sqft > 3_500:
        compliance_notes.append(
            "Large footprint may require intermediate bearing walls or steel beams — "
            "confirm with a licensed structural engineer."
        )

    return EngineeringReport(
        foundation_type=foundation,
        structural_system=structural_system,
        load_calculations=load_calculations,
        material_specs=material_specs,
        compliance_notes=compliance_notes,
    )


def generate_mep_plan(design: DesignOption) -> MEPPlan:
    """Generate a mock Mechanical / Electrical / Plumbing plan for *design*.

    Parameters
    ----------
    design:
        A ``DesignOption`` produced by the plan generator.

    Returns
    -------
    MEPPlan
        High-level MEP sizing and cost estimate.
    """
    sqft = design.total_sqft
    floors = max(r.floor for r in design.rooms) if design.rooms else 1

    # ── Electrical ──────────────────────────────────────────────────
    # Rule of thumb: ~1 circuit per 500-600 sqft + dedicated circuits
    base_circuits = max(8, math.ceil(sqft / 500))
    # Dedicated circuits: kitchen (2), laundry (1), HVAC (1), water heater (1),
    # garage (1 if present), each bathroom (1)
    bathroom_count = sum(
        1 for r in design.rooms if "bath" in r.room_name.lower()
    )
    has_garage = any("garage" in r.room_name.lower() for r in design.rooms)
    dedicated_circuits = 5 + bathroom_count + (1 if has_garage else 0)
    electrical_circuits = base_circuits + dedicated_circuits

    # ── Plumbing ────────────────────────────────────────────────────
    # Count fixtures from rooms
    plumbing_fixtures = 0
    for room in design.rooms:
        name_lower = room.room_name.lower()
        if "primary bath" in name_lower:
            plumbing_fixtures += 4  # toilet, dual sinks, tub/shower
        elif "half bath" in name_lower:
            plumbing_fixtures += 2  # toilet, sink
        elif "bath" in name_lower:
            plumbing_fixtures += 3  # toilet, sink, tub/shower
        elif "kitchen" in name_lower:
            plumbing_fixtures += 2  # sink, dishwasher
        elif "laundry" in name_lower:
            plumbing_fixtures += 2  # washer supply, utility sink
    plumbing_fixtures = max(plumbing_fixtures, 6)

    # ── HVAC ────────────────────────────────────────────────────────
    # Rule of thumb: 1 ton per 500-600 sqft (moderate climate)
    hvac_tonnage = round(max(1.5, sqft / 550), 1)
    if floors >= 2:
        # Multi-zone adds ~0.5 ton for distribution
        hvac_tonnage = round(hvac_tonnage + 0.5, 1)

    # ── Cost estimate ───────────────────────────────────────────────
    electrical_cost = electrical_circuits * 280 + sqft * 6  # wiring per sqft
    plumbing_cost = plumbing_fixtures * 750 + sqft * 4     # piping per sqft
    hvac_cost = hvac_tonnage * 3_200 + sqft * 3            # ductwork per sqft
    estimated_cost = int(electrical_cost + plumbing_cost + hvac_cost)

    return MEPPlan(
        electrical_circuits=electrical_circuits,
        plumbing_fixtures=plumbing_fixtures,
        hvac_tonnage=hvac_tonnage,
        estimated_cost=estimated_cost,
    )
