import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Order, OrderStatus
from app.services.audit import log_action
from app.services.orders import fulfill_paid_order
from app.services.payments import parse_yookassa_webhook
from app.services.yookassa_security import verify_yookassa_ip

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/yookassa")
async def yookassa_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    verify_yookassa_ip(request)
    body = await request.json()
    event, payment_id, order_id_str = parse_yookassa_webhook(body)

    await log_action(db, "webhook_received", details={"provider": "yookassa", "event": event, "payment_id": payment_id})

    if event != "payment.succeeded":
        await db.commit()
        return {"status": "ignored"}

    if not order_id_str:
        await db.commit()
        raise HTTPException(status_code=400, detail="missing order_id in metadata")

    try:
        order_id = UUID(order_id_str)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="invalid order_id") from e

    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="order not found")

    if order.status == OrderStatus.paid and order.email_sent_at:
        await db.commit()
        return {"status": "already_fulfilled"}

    await fulfill_paid_order(db, order_id, payment_id)
    await db.commit()
    return {"status": "ok"}


@router.post("/mock/{order_id}")
async def mock_webhook(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Simulate successful payment (development / mock provider)."""
    from app.config import get_settings

    if get_settings().payment_provider != "mock":
        raise HTTPException(status_code=403, detail="mock webhook only in mock mode")

    await fulfill_paid_order(db, order_id, f"mock_{order_id}")
    await db.commit()
    return {"status": "ok"}
