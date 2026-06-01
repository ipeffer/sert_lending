import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base
from app.models import CertificateCode, CodeStatus, Denomination, Order, OrderStatus
from app.services.orders import fulfill_paid_order


@pytest.fixture
async def paid_order_setup():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        denom = Denomination(variant="spa", nominal_rub=3000, price_rub=3000)
        db.add(denom)
        await db.flush()
        order_id = uuid.uuid4()
        order = Order(
            id=order_id,
            public_token="test-token",
            denomination_id=denom.id,
            variant="spa",
            nominal_rub=3000,
            amount_rub=3000,
            buyer_name="Test",
            buyer_email="test@example.com",
            buyer_phone="+79001234567",
            consent_pd=True,
            consent_privacy=True,
            status=OrderStatus.pending_payment,
            payment_provider="mock",
        )
        db.add(order)
        code = CertificateCode(
            denomination_id=denom.id,
            code="CODE-1",
            pin="1111",
            status=CodeStatus.reserved,
            order_id=order_id,
        )
        db.add(code)
        await db.commit()

    yield factory, order_id
    await engine.dispose()


@pytest.mark.asyncio
async def test_fulfill_idempotent(paid_order_setup):
    factory, order_id = paid_order_setup

    async with factory() as db:
        o1 = await fulfill_paid_order(db, order_id, "pay_123")
        await db.commit()

    async with factory() as db:
        o2 = await fulfill_paid_order(db, order_id, "pay_123")
        await db.commit()

    assert o1.status in (OrderStatus.paid, OrderStatus.paid_pending_delivery)
    assert o2.status == o1.status
