"""Mock Twilio SMS integration client.

Logs every outbound SMS and returns a successful-delivery response with
a generated SID.  No real messages are ever sent.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from vibehouse.integrations.base import BaseIntegration


class SMSClient(BaseIntegration):
    """Mock SMS client backed by Twilio-style responses."""

    DEFAULT_FROM = "+18005551234"

    def __init__(self) -> None:
        super().__init__("twilio")

    async def health_check(self) -> bool:
        self.logger.info("Twilio health check: OK (mock)")
        return True

    # ------------------------------------------------------------------
    # SMS
    # ------------------------------------------------------------------

    async def send_sms(self, to: str, body: str) -> dict[str, Any]:
        """Send an SMS message.

        Returns a dict mimicking Twilio's ``MessageInstance`` response.
        """
        sid = f"SM{uuid.uuid4().hex}"

        self.logger.info(
            "Mock SMS sent | from=%s | to=%s | body_length=%d | sid=%s",
            self.DEFAULT_FROM,
            to,
            len(body),
            sid,
        )

        return {
            "status": "sent",
            "sid": sid,
            "from": self.DEFAULT_FROM,
            "to": to,
            "body": body,
            "num_segments": max(1, (len(body) + 159) // 160),
            "direction": "outbound-api",
            "date_created": datetime.now(timezone.utc).isoformat(),
        }
