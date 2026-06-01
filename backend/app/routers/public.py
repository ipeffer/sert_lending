from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Order, OrderStatus
from app.services.certificate_delivery import get_certificate_pdf_for_order
from app.schemas import (
    CatalogResponse,
    CreateOrderRequest,
    CreateOrderResponse,
    OrderStatusResponse,
)
from app.services.orders import build_catalog, create_order
from app.services.payments import PaymentError

router = APIRouter(prefix="/api", tags=["public"])


@router.get("/catalog", response_model=CatalogResponse)
async def catalog(db: AsyncSession = Depends(get_db)) -> CatalogResponse:
    return await build_catalog(db)


@router.post("/orders", response_model=CreateOrderResponse)
async def post_order(
    body: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
) -> CreateOrderResponse:
    try:
        order = await create_order(
            db,
            denomination_id=body.denomination_id,
            buyer_name=body.buyer_name,
            buyer_email=str(body.buyer_email),
            buyer_phone=body.buyer_phone,
            consent_pd=body.consent_pd,
            consent_privacy=body.consent_privacy,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        code = str(e)
        if code == "no_stock":
            raise HTTPException(status_code=409, detail="Нет сертификатов выбранного номинала") from e
        if code == "consent_required":
            raise HTTPException(status_code=400, detail="Необходимо согласие с условиями") from e
        raise HTTPException(status_code=400, detail=code) from e
    except PaymentError as e:
        await db.rollback()
        raise HTTPException(status_code=502, detail=str(e)) from e

    return CreateOrderResponse(
        order_id=order.id,
        public_token=order.public_token,
        redirect_url=order.redirect_url or "",
    )


@router.get("/orders/{public_token}", response_model=OrderStatusResponse)
async def order_status(
    public_token: str,
    db: AsyncSession = Depends(get_db),
) -> OrderStatusResponse:
    result = await db.execute(select(Order).where(Order.public_token == public_token))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    can_download = order.status in (OrderStatus.paid, OrderStatus.paid_pending_delivery)
    return OrderStatusResponse(
        public_token=order.public_token,
        status=order.status.value,
        amount_rub=order.amount_rub,
        nominal_rub=order.nominal_rub,
        variant=order.variant,
        buyer_email=order.buyer_email,
        certificate_delivered=order.email_sent_at is not None,
        can_download_certificate=can_download,
    )


@router.get("/orders/{public_token}/certificate.pdf")
async def download_certificate(
    public_token: str,
    db: AsyncSession = Depends(get_db),
):
    result = await get_certificate_pdf_for_order(db, public_token)
    if not result:
        raise HTTPException(status_code=404, detail="Сертификат недоступен")
    pdf, filename = result
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
