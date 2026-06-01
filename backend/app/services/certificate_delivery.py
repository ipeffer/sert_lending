import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CertificateCode, CodeStatus, Order, OrderStatus
from app.services.pdf import build_certificate_pdf


async def get_certificate_pdf_for_order(db: AsyncSession, public_token: str) -> tuple[bytes, str] | None:
    result = await db.execute(select(Order).where(Order.public_token == public_token))
    order = result.scalar_one_or_none()
    if not order:
        return None

    if order.status not in (OrderStatus.paid, OrderStatus.paid_pending_delivery):
        return None

    code_result = await db.execute(
        select(CertificateCode).where(
            CertificateCode.order_id == order.id,
            CertificateCode.status == CodeStatus.sold,
        )
    )
    code = code_result.scalar_one_or_none()
    if not code:
        return None

    pdf = build_certificate_pdf(
        variant=order.variant,
        nominal_rub=order.nominal_rub,
        code=code.code,
        pin=code.pin,
        valid_until=code.valid_until,
        buyer_name=order.buyer_name,
    )
    filename = f"test-spa-certificate-{order.nominal_rub}.pdf"
    return pdf, filename
