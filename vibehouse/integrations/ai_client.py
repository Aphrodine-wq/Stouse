"""Mock AI / LLM integration client.

Provides realistic fake responses for vibe parsing, design summaries,
dispute analysis, and report generation -- all without calling any
external model API.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from vibehouse.integrations.base import BaseIntegration


class AIClient(BaseIntegration):
    """Mock AI client that returns pre-built realistic responses."""

    def __init__(self) -> None:
        super().__init__("ai")

    async def health_check(self) -> bool:
        self.logger.info("AI client health check: OK (mock)")
        return True

    # ------------------------------------------------------------------
    # Vibe parsing
    # ------------------------------------------------------------------

    async def parse_vibe_description(self, text: str) -> dict[str, Any]:
        """Parse a homeowner's natural-language vibe description into a
        structured JSON representation.

        Returns a dict with extracted style keywords, colour palette,
        material preferences, priority areas, and a confidence score.
        """
        self.logger.info(
            "Parsing vibe description (%d chars): %.60s...", len(text), text
        )

        parsed: dict[str, Any] = {
            "id": uuid.uuid4().hex,
            "source_text": text,
            "style_keywords": [
                "modern farmhouse",
                "warm minimalism",
                "organic textures",
            ],
            "color_palette": {
                "primary": "#F5F0EB",
                "secondary": "#3B3A36",
                "accent": "#C8A882",
                "neutral": "#E8E0D8",
            },
            "material_preferences": [
                {"material": "white oak", "usage": "flooring, cabinetry"},
                {"material": "natural stone", "usage": "countertops, fireplace surround"},
                {"material": "matte black hardware", "usage": "fixtures, cabinet pulls"},
                {"material": "linen", "usage": "drapery, upholstery"},
            ],
            "priority_areas": [
                {"area": "kitchen", "priority": "high", "notes": "Open-concept with island"},
                {"area": "primary bathroom", "priority": "high", "notes": "Spa-like atmosphere"},
                {"area": "living room", "priority": "medium", "notes": "Cozy yet uncluttered"},
            ],
            "budget_signals": {
                "tier": "mid-to-high",
                "keywords_detected": ["quality", "investment pieces", "long-lasting"],
            },
            "confidence": 0.87,
        }
        self.logger.info("Vibe parsed successfully (confidence=%.2f)", parsed["confidence"])
        return parsed

    # ------------------------------------------------------------------
    # Design summary
    # ------------------------------------------------------------------

    async def generate_design_summary(self, design_data: dict[str, Any]) -> str:
        """Generate a human-readable design summary from structured data."""
        self.logger.info(
            "Generating design summary for project '%s'",
            design_data.get("project_name", "unknown"),
        )

        project_name = design_data.get("project_name", "Your Home")
        room_count = len(design_data.get("rooms", []))
        style = design_data.get("style", "modern farmhouse")

        summary = (
            f"Design Summary for {project_name}\n"
            f"{'=' * 40}\n\n"
            f"Overall Style Direction: {style.title()}\n\n"
            f"This design concept embraces a {style} aesthetic that balances "
            f"warmth with clean, contemporary lines. Across the {room_count or 4} "
            f"rooms in scope, the palette draws from earthy neutrals -- warm "
            f"whites, soft taupes, and muted charcoals -- punctuated by organic "
            f"textures such as white oak, natural linen, and hand-finished "
            f"ceramics.\n\n"
            f"Key Design Decisions:\n"
            f"  - Flooring: Wide-plank white oak throughout main living areas\n"
            f"  - Kitchen: Shaker-style cabinetry in a warm off-white with "
            f"natural stone countertops and matte black hardware\n"
            f"  - Primary Bath: Floor-to-ceiling porcelain tile in a soft "
            f"grey with a freestanding soaking tub and brushed brass fixtures\n"
            f"  - Living Room: Layered textiles (linen, wool, jute) anchored "
            f"by a low-profile sectional and statement lighting\n\n"
            f"Material Budget Allocation:\n"
            f"  - Hard surfaces (flooring, tile, counters): ~45%\n"
            f"  - Cabinetry & millwork: ~25%\n"
            f"  - Fixtures & hardware: ~15%\n"
            f"  - Soft furnishings & decor: ~15%\n\n"
            f"Next Steps:\n"
            f"  1. Confirm material selections with vendor quotes\n"
            f"  2. Finalize fixture schedule for plumbing and electrical\n"
            f"  3. Review 3-D renderings with homeowner before procurement\n"
        )

        self.logger.info("Design summary generated (%d chars)", len(summary))
        return summary

    # ------------------------------------------------------------------
    # Dispute analysis
    # ------------------------------------------------------------------

    async def analyze_dispute(self, dispute_data: dict[str, Any]) -> dict[str, Any]:
        """Analyze a dispute between homeowner and vendor and return a
        structured recommendation.
        """
        dispute_id = dispute_data.get("dispute_id", uuid.uuid4().hex[:12])
        self.logger.info("Analyzing dispute %s", dispute_id)

        analysis: dict[str, Any] = {
            "dispute_id": dispute_id,
            "severity": "medium",
            "category": "scope_disagreement",
            "summary": (
                "The homeowner expected the tile installation to include "
                "removal of the existing backsplash, while the vendor's scope "
                "of work only covered installation over the prepared surface. "
                "The original project description is ambiguous on this point."
            ),
            "key_findings": [
                {
                    "finding": "Scope document does not explicitly mention demo",
                    "supports": "vendor",
                },
                {
                    "finding": "Homeowner's messages reference 'full backsplash redo'",
                    "supports": "homeowner",
                },
                {
                    "finding": "Industry standard for tile jobs typically includes "
                    "surface prep but not full demo unless specified",
                    "supports": "vendor",
                },
            ],
            "recommendation": {
                "action": "split_cost",
                "detail": (
                    "Recommend splitting the additional demo cost 50/50 as the "
                    "scope language was ambiguous. Issue a change order for the "
                    "demo work at the agreed split."
                ),
                "estimated_additional_cost": 450.00,
                "homeowner_share": 225.00,
                "vendor_share": 225.00,
            },
            "confidence": 0.79,
            "escalation_needed": False,
        }

        self.logger.info(
            "Dispute analysis complete: severity=%s, confidence=%.2f",
            analysis["severity"],
            analysis["confidence"],
        )
        return analysis

    # ------------------------------------------------------------------
    # Report summary
    # ------------------------------------------------------------------

    async def generate_report_summary(self, report_data: dict[str, Any]) -> str:
        """Generate a human-readable summary of a project report."""
        project_name = report_data.get("project_name", "Home Renovation")
        self.logger.info("Generating report summary for '%s'", project_name)

        total_budget = report_data.get("total_budget", 85000)
        spent = report_data.get("spent", 52340)
        completion_pct = report_data.get("completion_pct", 62)
        open_items = report_data.get("open_items", 7)
        overdue_items = report_data.get("overdue_items", 2)

        summary = (
            f"Project Status Report -- {project_name}\n"
            f"{'=' * 50}\n\n"
            f"Budget: ${spent:,.2f} of ${total_budget:,.2f} spent "
            f"({spent / total_budget * 100:.0f}% consumed)\n"
            f"Completion: {completion_pct}%\n"
            f"Open Work Items: {open_items} ({overdue_items} overdue)\n\n"
            f"Highlights:\n"
            f"  - Kitchen cabinetry installation completed on schedule\n"
            f"  - Plumbing rough-in passed inspection on first attempt\n"
            f"  - Tile delivery delayed by 5 business days (supplier backorder)\n\n"
            f"Risks & Concerns:\n"
            f"  - Tile delay may push bathroom completion past target date\n"
            f"  - Electrical panel upgrade quote came in 12% over estimate\n\n"
            f"Recommended Actions:\n"
            f"  1. Confirm revised tile delivery date with supplier\n"
            f"  2. Approve or negotiate electrical panel change order\n"
            f"  3. Schedule mid-project walkthrough with homeowner\n"
        )

        self.logger.info("Report summary generated (%d chars)", len(summary))
        return summary
