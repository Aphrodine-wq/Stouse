"""Mock SendGrid email integration client.

Logs every outbound email and returns a successful-send response with a
generated message ID.  No real emails are ever sent.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from vibehouse.integrations.base import BaseIntegration


class EmailClient(BaseIntegration):
    """Mock email client backed by SendGrid-style responses."""

    DEFAULT_FROM = "no-reply@vibehouse.app"

    def __init__(self) -> None:
        super().__init__("sendgrid")

    async def health_check(self) -> bool:
        self.logger.info("SendGrid health check: OK (mock)")
        return True

    # ------------------------------------------------------------------
    # Direct email
    # ------------------------------------------------------------------

    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        from_email: str | None = None,
    ) -> dict[str, Any]:
        """Send a single HTML email.

        Returns a dict mimicking SendGrid's accepted response.
        """
        message_id = str(uuid.uuid4())
        sender = from_email or self.DEFAULT_FROM

        self.logger.info(
            "Mock email sent | from=%s | to=%s | subject='%s' | body_length=%d | message_id=%s",
            sender,
            to,
            subject,
            len(html_body),
            message_id,
        )

        return {
            "status": "sent",
            "message_id": message_id,
            "from": sender,
            "to": to,
            "subject": subject,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Template email
    # ------------------------------------------------------------------

    async def send_template(
        self,
        to: str,
        template_id: str,
        template_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Send an email using a pre-defined SendGrid template.

        ``template_data`` is the dynamic data dict that would be merged
        into the template at send time.
        """
        message_id = str(uuid.uuid4())

        self.logger.info(
            "Mock template email sent | to=%s | template_id=%s | "
            "dynamic_keys=%s | message_id=%s",
            to,
            template_id,
            list(template_data.keys()),
            message_id,
        )

        return {
            "status": "sent",
            "message_id": message_id,
            "to": to,
            "template_id": template_id,
            "template_data_keys": list(template_data.keys()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
