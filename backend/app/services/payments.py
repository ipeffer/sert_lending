import base64
import logging
import uuid
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    pass


async def create_payment(
    *,
    order_id: uuid.UUID,
    amount_rub: int,
    description: str,
    buyer_email: str,
) -> tuple[str, str]:
    """Returns (external_payment_id, redirect_url)."""
    settings = get_settings()
    provider = settings.payment_provider.lower()

    if provider == "mock":
        ext_id = f"mock_{order_id}"
        redirect = (
            f"{settings.public_base_url}/payment/mock"
            f"?order={order_id}"
        )
        return ext_id, redirect

    if provider == "yookassa":
        return await _yookassa_create_payment(
            order_id=order_id,
            amount_rub=amount_rub,
            description=description,
            buyer_email=buyer_email,
        )

    raise PaymentError(f"Unknown payment provider: {provider}")


async def _yookassa_create_payment(
    *,
    order_id: uuid.UUID,
    amount_rub: int,
    description: str,
    buyer_email: str,
) -> tuple[str, str]:
    settings = get_settings()
    if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
        raise PaymentError("YooKassa credentials not configured")

    idempotence_key = str(order_id)
    auth = base64.b64encode(
        f"{settings.yookassa_shop_id}:{settings.yookassa_secret_key}".encode()
    ).decode()

    payload: dict[str, Any] = {
        "amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
        "confirmation": {
            "type": "redirect",
            "return_url": f"{settings.yookassa_return_url}?token={order_id}",
        },
        "capture": True,
        "description": description[:128],
        "metadata": {"order_id": str(order_id)},
        "receipt": {
            "customer": {"email": buyer_email},
            "items": [
                {
                    "description": description[:128],
                    "quantity": "1.00",
                    "amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
                    "vat_code": 1,
                    "payment_mode": "full_payment",
                    "payment_subject": "service",
                }
            ],
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.yookassa.ru/v3/payments",
            json=payload,
            headers={
                "Authorization": f"Basic {auth}",
                "Idempotence-Key": idempotence_key,
                "Content-Type": "application/json",
            },
        )
    if resp.status_code >= 400:
        logger.error("YooKassa error: %s", resp.text)
        raise PaymentError(f"YooKassa HTTP {resp.status_code}")

    data = resp.json()
    payment_id = data["id"]
    redirect_url = data["confirmation"]["confirmation_url"]
    return payment_id, redirect_url


def parse_yookassa_webhook(body: dict[str, Any]) -> tuple[str, str, str | None]:
    """Returns (event_type, payment_id, order_id from metadata)."""
    event = body.get("event", "")
    obj = body.get("object") or {}
    payment_id = obj.get("id", "")
    order_id = (obj.get("metadata") or {}).get("order_id")
    return event, payment_id, order_id
