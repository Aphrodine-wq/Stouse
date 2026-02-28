"""High-level orchestration service for the Vibe Engine.

``VibeEngineService`` ties together every stage of the vibe-to-plan
pipeline and persists results as ``DesignArtifact`` records in the
database.
"""

from __future__ import annotations

import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.common.enums import DesignArtifactType
from vibehouse.core.vibe_engine.cost_estimator import estimate_costs
from vibehouse.core.vibe_engine.engineering import analyze_structure, generate_mep_plan
from vibehouse.core.vibe_engine.plan_generator import generate_plans
from vibehouse.core.vibe_engine.vibe_parser import parse_vibe
from vibehouse.db.models.design import DesignArtifact


class VibeEngineService:
    """Facade that runs the full vibe-to-plan pipeline and persists results.

    Usage::

        service = VibeEngineService()
        artifacts = await service.process_vibe(
            project_id="<uuid>",
            vibe_text="I want a modern 4-bedroom...",
            db=async_session,
        )
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def process_vibe(
        self,
        project_id: str,
        vibe_text: str,
        db: AsyncSession,
    ) -> list[DesignArtifact]:
        """Run the complete vibe-to-plan pipeline.

        1. Parse the natural-language *vibe_text* into a requirement spec.
        2. Generate three floor-plan design options.
        3. For each option, run engineering analysis and cost estimation.
        4. Persist every output as a ``DesignArtifact`` row.

        Parameters
        ----------
        project_id:
            UUID (as string) of the parent project.
        vibe_text:
            Free-form homeowner description of their dream home.
        db:
            An active ``AsyncSession`` for database writes.

        Returns
        -------
        list[DesignArtifact]
            All created artifact records (floor plans, engineering
            reports, MEP plans, and cost estimates).
        """
        proj_uuid = uuid.UUID(project_id)

        # Stage 1 — Parse the vibe
        rso = parse_vibe(vibe_text)

        # Stage 2 — Generate floor-plan options
        design_options = generate_plans(rso)

        artifacts: list[DesignArtifact] = []

        for design in design_options:
            # ── Floor-plan artifact ─────────────────────────────────
            floor_plan_artifact = DesignArtifact(
                id=uuid.uuid4(),
                project_id=proj_uuid,
                artifact_type=DesignArtifactType.FLOOR_PLAN,
                version=1,
                title=f"Floor Plan — {design.title}",
                description=design.description,
                file_url=design.floor_plan_url,
                metadata_={
                    "option_id": design.option_id,
                    "total_sqft": design.total_sqft,
                    "estimated_cost": design.estimated_cost,
                    "style_score": design.style_score,
                    "efficiency_score": design.efficiency_score,
                    "rooms": [r.model_dump() for r in design.rooms],
                    "rso": rso.model_dump(),
                },
                is_selected=False,
            )
            db.add(floor_plan_artifact)
            artifacts.append(floor_plan_artifact)

            # ── Engineering / Structural artifact ───────────────────
            eng_report = analyze_structure(design)
            structural_artifact = DesignArtifact(
                id=uuid.uuid4(),
                project_id=proj_uuid,
                artifact_type=DesignArtifactType.STRUCTURAL,
                version=1,
                title=f"Structural Report — {design.title}",
                description=(
                    f"Foundation: {eng_report.foundation_type}. "
                    f"System: {eng_report.structural_system}."
                ),
                file_url=None,
                metadata_={
                    "option_id": design.option_id,
                    "foundation_type": eng_report.foundation_type,
                    "structural_system": eng_report.structural_system,
                    "load_calculations": eng_report.load_calculations,
                    "material_specs": eng_report.material_specs,
                    "compliance_notes": eng_report.compliance_notes,
                },
                is_selected=False,
            )
            db.add(structural_artifact)
            artifacts.append(structural_artifact)

            # ── MEP artifact ────────────────────────────────────────
            mep = generate_mep_plan(design)
            mep_artifact = DesignArtifact(
                id=uuid.uuid4(),
                project_id=proj_uuid,
                artifact_type=DesignArtifactType.MEP,
                version=1,
                title=f"MEP Plan — {design.title}",
                description=(
                    f"{mep.electrical_circuits} circuits, "
                    f"{mep.plumbing_fixtures} plumbing fixtures, "
                    f"{mep.hvac_tonnage}-ton HVAC."
                ),
                file_url=None,
                metadata_={
                    "option_id": design.option_id,
                    "electrical_circuits": mep.electrical_circuits,
                    "plumbing_fixtures": mep.plumbing_fixtures,
                    "hvac_tonnage": mep.hvac_tonnage,
                    "estimated_cost": mep.estimated_cost,
                },
                is_selected=False,
            )
            db.add(mep_artifact)
            artifacts.append(mep_artifact)

            # ── Cost estimate artifact ──────────────────────────────
            cost = estimate_costs(design)
            cost_artifact = DesignArtifact(
                id=uuid.uuid4(),
                project_id=proj_uuid,
                artifact_type=DesignArtifactType.COST_ESTIMATE,
                version=1,
                title=f"Cost Estimate — {design.title}",
                description=(
                    f"Grand total: ${cost.grand_total:,.0f} "
                    f"(materials: ${cost.total_materials:,.0f}, "
                    f"labor: ${cost.total_labor:,.0f}, "
                    f"contingency: ${cost.contingency:,.0f})."
                ),
                file_url=None,
                metadata_={
                    "option_id": design.option_id,
                    "materials": [m.model_dump() for m in cost.materials],
                    "labor_costs": cost.labor_costs,
                    "total_materials": cost.total_materials,
                    "total_labor": cost.total_labor,
                    "contingency": cost.contingency,
                    "grand_total": cost.grand_total,
                },
                is_selected=False,
            )
            db.add(cost_artifact)
            artifacts.append(cost_artifact)

        # Flush so callers can read generated IDs without committing the
        # transaction (the caller controls commit/rollback).
        await db.flush()

        return artifacts
