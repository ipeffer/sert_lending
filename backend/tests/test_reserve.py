import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base
from app.models import CertificateCode, CodeStatus, Denomination
from app.services.certificates import reserve_code


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        denom = Denomination(variant="spa", nominal_rub=3000, price_rub=3000)
        db.add(denom)
        await db.flush()
        db.add(
            CertificateCode(
                denomination_id=denom.id,
                code="ONLY-ONE",
                status=CodeStatus.available,
            )
        )
        await db.commit()
        yield factory, denom.id
    await engine.dispose()


@pytest.mark.asyncio
async def test_second_reserve_fails_when_one_code(session):
    """SQLite has no SKIP LOCKED; sequential test validates business rules."""
    factory, denom_id = session
    order_a = uuid.uuid4()
    order_b = uuid.uuid4()

    async with factory() as s:
        code = await reserve_code(s, denomination_id=denom_id, order_id=order_a)
        await s.commit()
        assert code.code == "ONLY-ONE"

    async with factory() as s:
        with pytest.raises(ValueError, match="no_stock"):
            await reserve_code(s, denomination_id=denom_id, order_id=order_b)
