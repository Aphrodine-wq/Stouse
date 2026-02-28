"""Pydantic models for the Vibe Engine pipeline.

These schemas define the data structures flowing through each stage of the
Vibe Engine: requirement parsing, plan generation, engineering analysis,
and cost estimation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Requirement Specification Object (RSO)
# ---------------------------------------------------------------------------

class RequirementSpecification(BaseModel):
    """Structured requirements extracted from a natural-language vibe
    description.  This is the canonical input for all downstream generators.
    """

    bedrooms: int = Field(3, ge=1, le=20, description="Number of bedrooms")
    bathrooms: float = Field(
        2.0, ge=1, le=15, description="Number of bathrooms (0.5 = half bath)"
    )
    floors: int = Field(1, ge=1, le=4, description="Number of stories")
    style: str = Field(
        "modern",
        description="Architectural style (modern, farmhouse, craftsman, colonial, contemporary, ranch)",
    )
    budget_range: tuple[int, int] = Field(
        (250_000, 450_000),
        description="Low and high end of budget in USD",
    )
    lot_sqft: int = Field(
        8_000,
        ge=1_000,
        description="Available lot size in square feet",
    )
    target_sqft: int = Field(
        2_000,
        ge=400,
        description="Desired total living area in square feet",
    )
    special_requirements: list[str] = Field(
        default_factory=list,
        description="Free-form special requirements (e.g. 'home office', 'wine cellar')",
    )
    garage: bool = Field(True, description="Whether a garage is desired")
    outdoor_space: bool = Field(
        True, description="Whether dedicated outdoor living space is desired"
    )


# ---------------------------------------------------------------------------
# Floor-plan primitives
# ---------------------------------------------------------------------------

class RoomLayout(BaseModel):
    """A single room within a floor plan."""

    room_name: str = Field(..., description="Human-readable room name")
    sqft: int = Field(..., ge=20, description="Room area in square feet")
    floor: int = Field(1, ge=1, description="Which story this room is on")


class DesignOption(BaseModel):
    """One of the generated floor-plan options presented to the homeowner."""

    option_id: str = Field(..., description="Unique identifier for this option")
    title: str = Field(..., description="Short marketing title")
    description: str = Field(..., description="Detailed description of the design")
    total_sqft: int = Field(..., ge=400, description="Total living square footage")
    rooms: list[RoomLayout] = Field(
        default_factory=list, description="Room breakdown"
    )
    estimated_cost: int = Field(..., ge=0, description="Estimated total cost in USD")
    style_score: float = Field(
        ..., ge=0.0, le=10.0, description="How well this matches the requested style"
    )
    efficiency_score: float = Field(
        ..., ge=0.0, le=10.0, description="Space/cost efficiency rating"
    )
    floor_plan_url: str | None = Field(
        None, description="URL to the rendered floor-plan image"
    )


# ---------------------------------------------------------------------------
# Engineering & MEP
# ---------------------------------------------------------------------------

class EngineeringReport(BaseModel):
    """Structural engineering analysis for a design option."""

    foundation_type: str = Field(
        ..., description="Foundation type (slab, crawlspace, basement)"
    )
    structural_system: str = Field(
        ..., description="Primary structural system (wood frame, steel, ICF, etc.)"
    )
    load_calculations: dict[str, float] = Field(
        default_factory=dict,
        description="Key load values in PSF / PLF / kips",
    )
    material_specs: dict[str, str] = Field(
        default_factory=dict,
        description="Specification strings for primary structural materials",
    )
    compliance_notes: list[str] = Field(
        default_factory=list,
        description="Relevant building-code compliance notes",
    )


class MEPPlan(BaseModel):
    """Mechanical / Electrical / Plumbing high-level plan."""

    electrical_circuits: int = Field(
        ..., ge=1, description="Total number of electrical circuits"
    )
    plumbing_fixtures: int = Field(
        ..., ge=1, description="Total number of plumbing fixtures"
    )
    hvac_tonnage: float = Field(
        ..., ge=0.5, description="HVAC capacity in tons"
    )
    estimated_cost: int = Field(
        ..., ge=0, description="Estimated MEP cost in USD"
    )


# ---------------------------------------------------------------------------
# Cost Estimation
# ---------------------------------------------------------------------------

class MaterialItem(BaseModel):
    """A single line item on the materials bill."""

    name: str = Field(..., description="Material name")
    category: str = Field(..., description="Category (concrete, lumber, roofing, ...)")
    quantity: float = Field(..., ge=0, description="Quantity required")
    unit: str = Field(..., description="Unit of measure")
    unit_cost: float = Field(..., ge=0, description="Cost per unit in USD")
    total_cost: float = Field(..., ge=0, description="Line-item total in USD")


class CostEstimate(BaseModel):
    """Full cost estimate including materials, labor, and contingency."""

    materials: list[MaterialItem] = Field(
        default_factory=list, description="Itemized material costs"
    )
    labor_costs: dict[str, float] = Field(
        default_factory=dict,
        description="Labor costs broken down by trade (framing, electrical, ...)",
    )
    total_materials: float = Field(
        ..., ge=0, description="Sum of all material costs"
    )
    total_labor: float = Field(
        ..., ge=0, description="Sum of all labor costs"
    )
    contingency: float = Field(
        ..., ge=0, description="Contingency reserve (typically 10%)"
    )
    grand_total: float = Field(
        ..., ge=0, description="Total project cost estimate"
    )
