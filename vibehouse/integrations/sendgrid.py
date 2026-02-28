"""SendGrid email integration client.

Uses real SendGrid API when a valid key is configured, otherwise
falls back to logging-only mock mode.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from vibehouse.config import settings
from vibehouse.integrations.base import BaseIntegration


def _is_mock() -> bool:
    return settings.SENDGRID_API_KEY.startswith("mock_")


class EmailClient(BaseIntegration):
    """Email client with real SendGrid API and mock fallback."""

    DEFAULT_FROM = "no-reply@vibehouse.app"
    SENDGRID_URL = "https://api.sendgrid.com/v3"

    def __init__(self) -> None:
        super().__init__("sendgrid")

    async def health_check(self) -> bool:
        if _is_mock():
            self.logger.info("SendGrid health check: OK (mock)")
            return True
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.SENDGRID_URL}/scopes",
                    headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}"},
                )
                return resp.status_code == 200
        except Exception as e:
            self.logger.error("SendGrid health check failed: %s", e)
            return False

    async def send_email(
        self, to: str, subject: str, html_body: str, from_email: str | None = None,
    ) -> dict[str, Any]:
        sender = from_email or self.DEFAULT_FROM
        message_id = str(uuid.uuid4())

        if not _is_mock():
            self.logger.info("Sending email to=%s subject='%s'", to, subject)
            payload = {
                "personalizations": [{"to": [{"email": to}]}],
                "from": {"email": sender},
                "subject": subject,
                "content": [{"type": "text/html", "value": html_body}],
            }
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        f"{self.SENDGRID_URL}/mail/send",
                        headers={
                            "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                    resp.raise_for_status()
                    sg_id = resp.headers.get("X-Message-Id", message_id)
                    self.logger.info("Email sent via SendGrid: %s", sg_id)
                    return {"status": "sent", "message_id": sg_id, "from": sender, "to": to, "subject": subject, "timestamp": datetime.now(timezone.utc).isoformat()}
            except Exception as e:
                self.logger.error("SendGrid email failed: %s", e)
                return {"status": "failed", "error": str(e), "to": to}

        self.logger.info("Mock email | from=%s | to=%s | subject='%s'", sender, to, subject)
        return {"status": "sent", "message_id": message_id, "from": sender, "to": to, "subject": subject, "timestamp": datetime.now(timezone.utc).isoformat()}

    async def send_template(
        self, to: str, template_id: str, template_data: dict[str, Any],
    ) -> dict[str, Any]:
        message_id = str(uuid.uuid4())

        if not _is_mock():
            payload = {
                "personalizations": [{"to": [{"email": to}], "dynamic_template_data": template_data}],
                "from": {"email": self.DEFAULT_FROM},
                "template_id": template_id,
            }
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        f"{self.SENDGRID_URL}/mail/send",
                        headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}", "Content-Type": "application/json"},
                        json=payload,
                    )
                    resp.raise_for_status()
                    sg_id = resp.headers.get("X-Message-Id", message_id)
                    return {"status": "sent", "message_id": sg_id, "to": to, "template_id": template_id, "timestamp": datetime.now(timezone.utc).isoformat()}
            except Exception as e:
                self.logger.error("SendGrid template email failed: %s", e)
                return {"status": "failed", "error": str(e)}

        self.logger.info("Mock template email | to=%s | template=%s", to, template_id)
        return {"status": "sent", "message_id": message_id, "to": to, "template_id": template_id, "template_data_keys": list(template_data.keys()), "timestamp": datetime.now(timezone.utc).isoformat()}
