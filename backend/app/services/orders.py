import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import CertificateCode, CodeStatus, Denomination, Order, OrderStatus
from app.schemas import CatalogResponse, NominalOption
from app.services.audit import log_action
from app.services.certificates import commit_sale, release_code_for_order, reserve_code
from app.services.email import send_certificate_email
from app.services.pdf import build_certificate_pdf
from app.services.payments import PaymentError, create_payment


def _public_token() -> str:
    return secrets.token_urlsafe(24)


async def build_catalog(db: AsyncSession) -> CatalogResponse:
    denoms = (
        await db.execute(
            select(Denomination).where(Denomination.is_active.is_(True)).order_by(Denomination.nominal_rub)
        )
    ).scalars().all()

    spa: list[NominalOption] = []
    ar: list[NominalOption] = []

    for d in denoms:
        cnt = (
            await db.execute(
                select(func.count(CertificateCode.id)).where(
                    CertificateCode.denomination_id == d.id,
                    CertificateCode.status == CodeStatus.available,
                )
            )
        ).scalar_one()
        opt = NominalOption(
            id=d.id,
            variant=d.variant,
            nominal_rub=d.nominal_rub,
            price_rub=d.price_rub,
            available_count=cnt,
            can_buy=cnt > 0,
        )
        if d.variant == "ar":
            ar.append(opt)
        else:
            spa.append(opt)

    return CatalogResponse(spa_nominals=spa, ar_nominals=ar)


async def create_order(
    db: AsyncSession,
    *,
    denomination_id: int,
    buyer_name: str,
    buyer_email: str,
    buyer_phone: str,
    consent_pd: bool,
    consent_privacy: bool,
) -> Order:
    if not consent_pd or not consent_privacy:
        raise ValueError("consent_required")

    denom = await db.get(Denomination, denomination_id)
    if not denom or not denom.is_active:
        raise ValueError("invalid_denomination")

    order = Order(
        public_token=_public_token(),
        denomination_id=denom.id,
        variant=denom.variant,
        nominal_rub=denom.nominal_rub,
        amount_rub=denom.price_rub,
        buyer_name=buyer_name.strip(),
        buyer_email=buyer_email.strip().lower(),
        buyer_phone=buyer_phone.strip(),
        consent_pd=consent_pd,
        consent_privacy=consent_privacy,
        status=OrderStatus.pending_payment,
        payment_provider=get_settings().payment_provider,
    )
    db.add(order)
    await db.flush()

    try:
        await reserve_code(db, denomination_id=denom.id, order_id=order.id)
    except ValueError as e:
        if str(e) == "no_stock":
            raise ValueError("no_stock") from e
        raise

    description = f"Подарочный сертификат Тестовая СПА продажа {denom.nominal_rub} ₽"
    try:
        ext_id, redirect = await create_payment(
            order_id=order.id,
            amount_rub=order.amount_rub,
            description=description,
            buyer_email=order.buyer_email,
        )
    except PaymentError:
        await release_code_for_order(db, order.id)
        order.status = OrderStatus.failed
        raise

    order.payment_external_id = ext_id
    order.redirect_url = redirect
    if get_settings().payment_provider == "mock":
        sep = "&" if "?" in (order.redirect_url or "") else "?"
        order.redirect_url = f"{order.redirect_url}{sep}token={order.public_token}"
    order.payment_idempotency_key = str(order.id)

    await log_action(
        db,
        "order_created",
        order_id=order.id,
        details={"amount": order.amount_rub, "denomination_id": denom.id},
    )
    return order


async def fulfill_paid_order(db: AsyncSession, order_id: uuid.UUID, payment_external_id: str) -> Order:
    order = await db.get(Order, order_id)
    if not order:
        raise ValueError("order_not_found")

    # Idempotent webhook: already delivered
    if order.status == OrderStatus.paid and order.email_sent_at:
        return order

    if payment_external_id and order.payment_external_id == payment_external_id:
        if order.status == OrderStatus.paid and order.email_sent_at:
            return order

    order.payment_external_id = payment_external_id or order.payment_external_id
    code = await commit_sale(db, order_id)
    if not code:
        order.status = OrderStatus.paid_pending_delivery
        await log_action(db, "fulfill_no_code", order_id=order_id)
        return order

    pdf = build_certificate_pdf(
        variant=order.variant,
        nominal_rub=order.nominal_rub,
        code=code.code,
        pin=code.pin,
        valid_until=code.valid_until,
        buyer_name=order.buyer_name,
    )
    sent = await send_certificate_email(
        to_email=order.buyer_email,
        buyer_name=order.buyer_name,
        nominal_rub=order.nominal_rub,
        pdf_bytes=pdf,
    )

    if sent:
        order.status = OrderStatus.paid
        order.email_sent_at = datetime.now(timezone.utc)
    else:
        order.status = OrderStatus.paid_pending_delivery

    await log_action(
        db,
        "order_fulfilled",
        order_id=order_id,
        details={"email_sent": sent, "code_id": code.id},
    )
    return order


async def retry_delivery(db: AsyncSession, order_id: uuid.UUID) -> Order:
    """Resend certificate email for paid_pending_delivery orders."""
    order = await db.get(Order, order_id)
    if not order:
        raise ValueError("order_not_found")
    if order.status not in (OrderStatus.paid_pending_delivery, OrderStatus.paid):
        raise ValueError("invalid_status")

    result = await db.execute(
        select(CertificateCode).where(
            CertificateCode.order_id == order_id,
            CertificateCode.status == CodeStatus.sold,
        )
    )
    code = result.scalar_one_or_none()
    if not code:
        raise ValueError("no_code")

    pdf = build_certificate_pdf(
        variant=order.variant,
        nominal_rub=order.nominal_rub,
        code=code.code,
        pin=code.pin,
        valid_until=code.valid_until,
        buyer_name=order.buyer_name,
    )
    sent = await send_certificate_email(
        to_email=order.buyer_email,
        buyer_name=order.buyer_name,
        nominal_rub=order.nominal_rub,
        pdf_bytes=pdf,
    )
    if sent:
        order.status = OrderStatus.paid
        order.email_sent_at = datetime.now(timezone.utc)
    await log_action(
        db,
        "delivery_retry",
        order_id=order_id,
        details={"email_sent": sent},
    )
    if not sent:
        raise ValueError("email_failed")
    return order


async def cancel_unpaid_order(db: AsyncSession, order_id: uuid.UUID) -> None:
    order = await db.get(Order, order_id)
    if not order or order.status != OrderStatus.pending_payment:
        return
    await release_code_for_order(db, order_id)
    order.status = OrderStatus.cancelled
    await log_action(db, "order_cancelled", order_id=order_id)
