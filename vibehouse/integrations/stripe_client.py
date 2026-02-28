"""Stripe payment integration client.

Uses real Stripe API when a valid key is configured, otherwise
falls back to mock payment responses for development.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from vibehouse.config import settings
from vibehouse.integrations.base import BaseIntegration


def _is_mock() -> bool:
    key = getattr(settings, "STRIPE_SECRET_KEY", "mock_stripe_key")
    return key.startswith("mock_")


class StripeClient(BaseIntegration):
    """Payment client with real Stripe API and mock fallback."""

    BASE_URL = "https://api.stripe.com/v1"

    def __init__(self) -> None:
        super().__init__("stripe")

    def _headers(self) -> dict[str, str]:
        key = getattr(settings, "STRIPE_SECRET_KEY", "")
        return {"Authorization": f"Bearer {key}"}

    async def health_check(self) -> bool:
        if _is_mock():
            self.logger.info("Stripe health check: OK (mock)")
            return True
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/balance",
                    headers=self._headers(),
                )
                return resp.status_code == 200
        except Exception as e:
            self.logger.error("Stripe health check failed: %s", e)
            return False

    # ------------------------------------------------------------------
    # Customers
    # ------------------------------------------------------------------

    async def create_customer(
        self, email: str, name: str, metadata: dict[str, str] | None = None
    ) -> dict[str, Any]:
        if not _is_mock():
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.BASE_URL}/customers",
                    headers=self._headers(),
                    data={
                        "email": email,
                        "name": name,
                        **({"metadata": metadata} if metadata else {}),
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                self.logger.info("Created Stripe customer: %s", data["id"])
                return data

        customer_id = f"cus_{uuid.uuid4().hex[:14]}"
        self.logger.info("Mock Stripe customer created: %s", customer_id)
        return {
            "id": customer_id,
            "object": "customer",
            "email": email,
            "name": name,
            "created": int(datetime.now(timezone.utc).timestamp()),
        }

    # ------------------------------------------------------------------
    # Payment Intents
    # ------------------------------------------------------------------

    async def create_payment_intent(
        self,
        amount_cents: int,
        currency: str = "usd",
        customer_id: str | None = None,
        description: str = "",
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if not _is_mock():
            payload: dict[str, Any] = {
                "amount": amount_cents,
                "currency": currency,
                "description": description,
            }
            if customer_id:
                payload["customer"] = customer_id
            if metadata:
                for k, v in metadata.items():
                    payload[f"metadata[{k}]"] = v
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.BASE_URL}/payment_intents",
                    headers=self._headers(),
                    data=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                self.logger.info("Created payment intent: %s ($%.2f)", data["id"], amount_cents / 100)
                return data

        pi_id = f"pi_{uuid.uuid4().hex[:24]}"
        client_secret = f"{pi_id}_secret_{uuid.uuid4().hex[:12]}"
        self.logger.info("Mock payment intent: %s ($%.2f)", pi_id, amount_cents / 100)
        return {
            "id": pi_id,
            "object": "payment_intent",
            "amount": amount_cents,
            "currency": currency,
            "status": "requires_payment_method",
            "client_secret": client_secret,
            "customer": customer_id,
            "description": description,
            "created": int(datetime.now(timezone.utc).timestamp()),
        }

    # ------------------------------------------------------------------
    # Invoices
    # ------------------------------------------------------------------

    async def create_invoice(
        self,
        customer_id: str,
        items: list[dict[str, Any]],
        description: str = "",
        due_days: int = 30,
    ) -> dict[str, Any]:
        if not _is_mock():
            # Create invoice
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.BASE_URL}/invoices",
                    headers=self._headers(),
                    data={
                        "customer": customer_id,
                        "description": description,
                        "collection_method": "send_invoice",
                        "days_until_due": due_days,
                    },
                )
                resp.raise_for_status()
                invoice = resp.json()

                # Add line items
                for item in items:
                    await client.post(
                        f"{self.BASE_URL}/invoiceitems",
                        headers=self._headers(),
                        data={
                            "customer": customer_id,
                            "invoice": invoice["id"],
                            "amount": item["amount_cents"],
                            "currency": item.get("currency", "usd"),
                            "description": item.get("description", ""),
                        },
                    )

                # Finalize invoice
                resp = await client.post(
                    f"{self.BASE_URL}/invoices/{invoice['id']}/finalize",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                final = resp.json()
                self.logger.info("Created Stripe invoice: %s", final["id"])
                return final

        inv_id = f"in_{uuid.uuid4().hex[:24]}"
        total = sum(item.get("amount_cents", 0) for item in items)
        self.logger.info("Mock invoice: %s ($%.2f)", inv_id, total / 100)
        return {
            "id": inv_id,
            "object": "invoice",
            "customer": customer_id,
            "status": "open",
            "total": total,
            "currency": "usd",
            "description": description,
            "due_date": int(datetime.now(timezone.utc).timestamp()) + (due_days * 86400),
            "hosted_invoice_url": f"https://invoice.stripe.com/i/{uuid.uuid4().hex[:20]}",
            "invoice_pdf": f"https://invoice.stripe.com/i/{uuid.uuid4().hex[:20]}/pdf",
            "lines": {
                "data": [
                    {
                        "id": f"il_{uuid.uuid4().hex[:14]}",
                        "amount": item.get("amount_cents", 0),
                        "description": item.get("description", ""),
                    }
                    for item in items
                ],
            },
            "created": int(datetime.now(timezone.utc).timestamp()),
        }

    # ------------------------------------------------------------------
    # Refunds
    # ------------------------------------------------------------------

    async def create_refund(
        self, payment_intent_id: str, amount_cents: int | None = None, reason: str = ""
    ) -> dict[str, Any]:
        if not _is_mock():
            payload: dict[str, Any] = {"payment_intent": payment_intent_id}
            if amount_cents:
                payload["amount"] = amount_cents
            if reason:
                payload["reason"] = reason
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.BASE_URL}/refunds",
                    headers=self._headers(),
                    data=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                self.logger.info("Created refund: %s", data["id"])
                return data

        ref_id = f"re_{uuid.uuid4().hex[:24]}"
        self.logger.info("Mock refund: %s", ref_id)
        return {
            "id": ref_id,
            "object": "refund",
            "amount": amount_cents or 0,
            "payment_intent": payment_intent_id,
            "status": "succeeded",
            "reason": reason,
            "created": int(datetime.now(timezone.utc).timestamp()),
        }

    # ------------------------------------------------------------------
    # Webhook signature verification
    # ------------------------------------------------------------------

    def verify_webhook_signature(self, payload: bytes, sig_header: str) -> dict[str, Any]:
        """Verify a Stripe webhook signature. Returns the parsed event."""
        import hashlib
        import hmac
        import json
        import time

        webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")

        if _is_mock() or not webhook_secret:
            return json.loads(payload)

        parts = dict(item.split("=", 1) for item in sig_header.split(","))
        timestamp = parts.get("t", "")
        signature = parts.get("v1", "")

        signed_payload = f"{timestamp}.{payload.decode()}"
        expected = hmac.new(
            webhook_secret.encode(), signed_payload.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid Stripe webhook signature")

        # Check timestamp is within 5 minutes
        if abs(time.time() - int(timestamp)) > 300:
            raise ValueError("Stripe webhook timestamp too old")

        return json.loads(payload)
