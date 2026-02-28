"""AI / LLM integration client.

Uses OpenAI-compatible API when a real key is configured, otherwise
falls back to realistic mock responses for development.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx

from vibehouse.config import settings
from vibehouse.integrations.base import BaseIntegration


def _is_mock() -> bool:
    return settings.AI_API_KEY.startswith("mock_")


class AIClient(BaseIntegration):
    """AI client that calls OpenAI (or compatible) API, with mock fallback."""

    def __init__(self) -> None:
        super().__init__("ai")
        self._base_url = getattr(settings, "AI_BASE_URL", "https://api.openai.com/v1")
        self._model = getattr(settings, "AI_MODEL", "gpt-4o")

    async def health_check(self) -> bool:
        if _is_mock():
            self.logger.info("AI client health check: OK (mock)")
            return True
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._base_url}/models",
                    headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
                )
                return resp.status_code == 200
        except Exception as e:
            self.logger.error("AI health check failed: %s", e)
            return False

    async def _chat(self, system: str, user: str, temperature: float = 0.7) -> str:
        if _is_mock():
            return ""
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.AI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _chat_json(self, system: str, user: str, temperature: float = 0.5) -> dict[str, Any]:
        raw = await self._chat(system, user, temperature)
        if not raw:
            return {}
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        return json.loads(text)

    # ------------------------------------------------------------------
    # Vibe parsing
    # ------------------------------------------------------------------

    async def parse_vibe_description(self, text: str) -> dict[str, Any]:
        self.logger.info("Parsing vibe description (%d chars): %.60s...", len(text), text)

        if not _is_mock():
            system = (
                "You are a home design AI. Parse the user's natural-language description of their "
                "dream home into structured JSON. Extract: style_keywords (list), color_palette "
                "(dict with primary/secondary/accent/neutral hex colors), material_preferences "
                "(list of {material, usage}), priority_areas (list of {area, priority, notes}), "
                "budget_signals ({tier, keywords_detected}), and confidence (0-1 float). "
                "Return ONLY valid JSON."
            )
            try:
                parsed = await self._chat_json(system, text)
                parsed["id"] = uuid.uuid4().hex
                parsed["source_text"] = text
                self.logger.info("Vibe parsed via LLM (confidence=%.2f)", parsed.get("confidence", 0))
                return parsed
            except Exception as e:
                self.logger.warning("LLM vibe parse failed, using fallback: %s", e)

        parsed: dict[str, Any] = {
            "id": uuid.uuid4().hex,
            "source_text": text,
            "style_keywords": ["modern farmhouse", "warm minimalism", "organic textures"],
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
        self.logger.info("Vibe parsed with mock (confidence=%.2f)", parsed["confidence"])
        return parsed

    # ------------------------------------------------------------------
    # Design summary
    # ------------------------------------------------------------------

    async def generate_design_summary(self, design_data: dict[str, Any]) -> str:
        self.logger.info(
            "Generating design summary for project '%s'",
            design_data.get("project_name", "unknown"),
        )

        if not _is_mock():
            system = (
                "You are a home design consultant. Generate a professional, detailed design "
                "summary from the structured data provided. Include style direction, key design "
                "decisions, material budget allocation, and next steps."
            )
            try:
                result = await self._chat(system, json.dumps(design_data))
                self.logger.info("Design summary generated via LLM (%d chars)", len(result))
                return result
            except Exception as e:
                self.logger.warning("LLM design summary failed, using fallback: %s", e)

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
            f"textures such as white oak, natural linen, and hand-finished ceramics.\n\n"
            f"Key Design Decisions:\n"
            f"  - Flooring: Wide-plank white oak throughout main living areas\n"
            f"  - Kitchen: Shaker-style cabinetry with natural stone countertops\n"
            f"  - Primary Bath: Floor-to-ceiling porcelain tile with soaking tub\n"
            f"  - Living Room: Layered textiles anchored by statement lighting\n\n"
            f"Material Budget Allocation:\n"
            f"  - Hard surfaces: ~45%\n"
            f"  - Cabinetry & millwork: ~25%\n"
            f"  - Fixtures & hardware: ~15%\n"
            f"  - Soft furnishings & decor: ~15%\n\n"
            f"Next Steps:\n"
            f"  1. Confirm material selections with vendor quotes\n"
            f"  2. Finalize fixture schedule for plumbing and electrical\n"
            f"  3. Review 3-D renderings with homeowner before procurement\n"
        )
        self.logger.info("Design summary generated with mock (%d chars)", len(summary))
        return summary

    # ------------------------------------------------------------------
    # Dispute analysis
    # ------------------------------------------------------------------

    async def analyze_dispute(self, dispute_data: dict[str, Any]) -> dict[str, Any]:
        dispute_id = dispute_data.get("dispute_id", uuid.uuid4().hex[:12])
        self.logger.info("Analyzing dispute %s", dispute_id)

        if not _is_mock():
            system = (
                "You are a construction dispute mediator AI. Analyze the dispute and return JSON with: "
                "dispute_id, severity (low/medium/high), category, summary, key_findings (list of "
                "{finding, supports: homeowner|vendor}), recommendation ({action, detail, "
                "estimated_additional_cost, homeowner_share, vendor_share}), confidence (0-1), "
                "escalation_needed (bool). Return ONLY valid JSON."
            )
            try:
                analysis = await self._chat_json(system, json.dumps(dispute_data))
                analysis["dispute_id"] = dispute_id
                self.logger.info("Dispute analyzed via LLM: severity=%s", analysis.get("severity"))
                return analysis
            except Exception as e:
                self.logger.warning("LLM dispute analysis failed, using fallback: %s", e)

        analysis: dict[str, Any] = {
            "dispute_id": dispute_id,
            "severity": "medium",
            "category": "scope_disagreement",
            "summary": (
                "The homeowner expected the tile installation to include "
                "removal of the existing backsplash, while the vendor's scope "
                "of work only covered installation over the prepared surface."
            ),
            "key_findings": [
                {"finding": "Scope document does not explicitly mention demo", "supports": "vendor"},
                {"finding": "Homeowner's messages reference 'full backsplash redo'", "supports": "homeowner"},
                {"finding": "Industry standard typically includes surface prep but not full demo", "supports": "vendor"},
            ],
            "recommendation": {
                "action": "split_cost",
                "detail": "Recommend splitting the additional demo cost 50/50.",
                "estimated_additional_cost": 450.00,
                "homeowner_share": 225.00,
                "vendor_share": 225.00,
            },
            "confidence": 0.79,
            "escalation_needed": False,
        }
        self.logger.info("Dispute analysis complete with mock: severity=%s", analysis["severity"])
        return analysis

    # ------------------------------------------------------------------
    # Report summary
    # ------------------------------------------------------------------

    async def generate_report_summary(self, report_data: dict[str, Any]) -> str:
        project_name = report_data.get("project_name", "Home Renovation")
        self.logger.info("Generating report summary for '%s'", project_name)

        if not _is_mock():
            system = (
                "You are a construction project manager AI. Generate a concise daily project status "
                "report from the data provided. Include budget status, completion %, highlights, "
                "risks, and recommended actions."
            )
            try:
                result = await self._chat(system, json.dumps(report_data))
                self.logger.info("Report summary generated via LLM (%d chars)", len(result))
                return result
            except Exception as e:
                self.logger.warning("LLM report summary failed, using fallback: %s", e)

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
            f"  - Tile delivery delayed by 5 business days\n\n"
            f"Risks & Concerns:\n"
            f"  - Tile delay may push bathroom completion past target\n"
            f"  - Electrical panel quote came in 12% over estimate\n\n"
            f"Recommended Actions:\n"
            f"  1. Confirm revised tile delivery date\n"
            f"  2. Approve or negotiate electrical panel change order\n"
            f"  3. Schedule mid-project walkthrough with homeowner\n"
        )
        self.logger.info("Report summary generated with mock (%d chars)", len(summary))
        return summary
