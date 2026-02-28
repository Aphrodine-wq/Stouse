"""Twilio SMS integration client.

Uses real Twilio REST API when valid credentials are configured,
otherwise falls back to logging-only mock mode.
"""

from __future__ import annotations

import uuid
from base64 import b64encode
from datetime import datetime, timezone
from typing import Any

import httpx

from vibehouse.config import settings
from vibehouse.integrations.base import BaseIntegration


def _is_mock() -> bool:
    return settings.TWILIO_ACCOUNT_SID.startswith("mock_")


class SMSClient(BaseIntegration):
    """SMS client with real Twilio API and mock fallback."""

    def __init__(self) -> None:
        super().__init__("twilio")

    @property
    def _from_number(self) -> str:
        return settings.TWILIO_FROM_NUMBER

    async def health_check(self) -> bool:
        if _is_mock():
            self.logger.info("Twilio health check: OK (mock)")
            return True
        try:
            auth = b64encode(f"{settings.TWILIO_ACCOUNT_SID}:{settings.TWILIO_AUTH_TOKEN}".encode()).decode()
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}.json",
                    headers={"Authorization": f"Basic {auth}"},
                )
                return resp.status_code == 200
        except Exception as e:
            self.logger.error("Twilio health check failed: %s", e)
            return False

    async def send_sms(self, to: str, body: str) -> dict[str, Any]:
        if not _is_mock():
            self.logger.info("Sending SMS to=%s", to)
            auth = b64encode(f"{settings.TWILIO_ACCOUNT_SID}:{settings.TWILIO_AUTH_TOKEN}".encode()).decode()
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json",
                        headers={"Authorization": f"Basic {auth}"},
                        data={"From": self._from_number, "To": to, "Body": body},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    self.logger.info("SMS sent via Twilio: sid=%s", data.get("sid"))
                    return {"status": "sent", "sid": data["sid"], "from": self._from_number, "to": to, "body": body, "date_created": data.get("date_created")}
            except Exception as e:
                self.logger.error("Twilio SMS failed: %s", e)
                return {"status": "failed", "error": str(e), "to": to}

        sid = f"SM{uuid.uuid4().hex}"
        self.logger.info("Mock SMS | from=%s | to=%s | len=%d", self._from_number, to, len(body))
        return {
            "status": "sent", "sid": sid, "from": self._from_number, "to": to, "body": body,
            "num_segments": max(1, (len(body) + 159) // 160), "direction": "outbound-api",
            "date_created": datetime.now(timezone.utc).isoformat(),
        }
