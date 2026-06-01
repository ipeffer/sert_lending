import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base
from app.models import CertificateCode, CodeStatus, Denomination, Order, OrderStatus
from app.services.certificate_delivery import get_certificate_pdf_for_order


@pytest.mark.asyncio
async def test_download_pdf_after_paid():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    token = "test-public-token-xyz"
    order_id = uuid.uuid4()

    async with factory() as db:
        denom = Denomination(variant="spa", nominal_rub=3000, price_rub=3000)
        db.add(denom)
        await db.flush()
        db.add(
            Order(
                id=order_id,
                public_token=token,
                denomination_id=denom.id,
                variant="spa",
                nominal_rub=3000,
                amount_rub=3000,
                buyer_name="Tester",
                buyer_email="t@test.ru",
                buyer_phone="+79001112233",
                consent_pd=True,
                consent_privacy=True,
                status=OrderStatus.paid,
                payment_provider="mock",
            )
        )
        db.add(
            CertificateCode(
                denomination_id=denom.id,
                code="DL-001",
                pin="9999",
                status=CodeStatus.sold,
                order_id=order_id,
            )
        )
        await db.commit()

    async with factory() as db:
        result = await get_certificate_pdf_for_order(db, token)
        assert result is not None
        pdf, name = result
        assert pdf[:4] == b"%PDF"
        assert "3000" in name

    await engine.dispose()
