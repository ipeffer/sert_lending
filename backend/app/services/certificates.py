import csv
import io
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import CertificateCode, CodeStatus, Denomination
from app.services.audit import log_action


async def get_or_create_denomination(
    db: AsyncSession,
    *,
    variant: str,
    nominal_rub: int,
) -> Denomination:
    result = await db.execute(
        select(Denomination).where(
            Denomination.variant == variant,
            Denomination.nominal_rub == nominal_rub,
        )
    )
    denom = result.scalar_one_or_none()
    if denom:
        return denom
    denom = Denomination(variant=variant, nominal_rub=nominal_rub, price_rub=nominal_rub, is_active=True)
    db.add(denom)
    await db.flush()
    return denom


async def stock_summary(db: AsyncSession) -> list[dict]:
    q = (
        select(
            Denomination.id,
            Denomination.variant,
            Denomination.nominal_rub,
            CertificateCode.status,
            func.count(CertificateCode.id),
        )
        .join(CertificateCode, CertificateCode.denomination_id == Denomination.id, isouter=True)
        .group_by(Denomination.id, Denomination.variant, Denomination.nominal_rub, CertificateCode.status)
    )
    rows = (await db.execute(q)).all()
    by_id: dict[int, dict] = {}
    for denom_id, variant, nominal, status, cnt in rows:
        if denom_id not in by_id:
            by_id[denom_id] = {
                "denomination_id": denom_id,
                "variant": variant,
                "nominal_rub": nominal,
                "available": 0,
                "reserved": 0,
                "sold": 0,
            }
        if status is None:
            continue
        key = status.value if hasattr(status, "value") else str(status)
        if key in by_id[denom_id]:
            by_id[denom_id][key] = cnt
    return list(by_id.values())


async def release_expired_reservations(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(CertificateCode)
        .where(
            CertificateCode.status == CodeStatus.reserved,
            CertificateCode.reserved_until < now,
        )
        .values(status=CodeStatus.available, reserved_until=None, order_id=None)
        .returning(CertificateCode.id)
    )
    released = len(result.fetchall())
    if released:
        await log_action(db, "reservations_released", details={"count": released})
    return released


async def reserve_code(db: AsyncSession, denomination_id: int, order_id: uuid.UUID) -> CertificateCode:
    settings = get_settings()
    await release_expired_reservations(db)

    # SELECT ... FOR UPDATE SKIP LOCKED
    result = await db.execute(
        select(CertificateCode)
        .where(
            CertificateCode.denomination_id == denomination_id,
            CertificateCode.status == CodeStatus.available,
        )
        .order_by(CertificateCode.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    code = result.scalar_one_or_none()
    if not code:
        raise ValueError("no_stock")

    until = datetime.now(timezone.utc) + timedelta(minutes=settings.reserve_ttl_minutes)
    code.status = CodeStatus.reserved
    code.reserved_until = until
    code.order_id = order_id
    await log_action(
        db,
        "code_reserved",
        order_id=order_id,
        details={"code_id": code.id, "denomination_id": denomination_id},
    )
    return code


async def commit_sale(db: AsyncSession, order_id: uuid.UUID) -> CertificateCode | None:
    result = await db.execute(
        select(CertificateCode).where(
            CertificateCode.order_id == order_id,
            CertificateCode.status.in_([CodeStatus.reserved, CodeStatus.sold]),
        )
    )
    code = result.scalar_one_or_none()
    if not code:
        return None
    if code.status == CodeStatus.sold:
        return code
    code.status = CodeStatus.sold
    code.sold_at = datetime.now(timezone.utc)
    code.reserved_until = None
    await log_action(db, "code_sold", order_id=order_id, details={"code_id": code.id})
    return code


async def release_code_for_order(db: AsyncSession, order_id: uuid.UUID) -> None:
    await db.execute(
        update(CertificateCode)
        .where(CertificateCode.order_id == order_id, CertificateCode.status == CodeStatus.reserved)
        .values(status=CodeStatus.available, reserved_until=None, order_id=None)
    )


def mask_code(code: str) -> str:
    if len(code) <= 4:
        return "****"
    return "*" * (len(code) - 4) + code[-4:]


async def import_csv(db: AsyncSession, content: bytes, actor: str = "admin") -> tuple[int, int, list[str]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    required = {"denomination_rub", "code"}
    if not reader.fieldnames or not required.issubset({h.strip().lower() for h in reader.fieldnames}):
        return 0, 0, ["Missing columns: denomination_rub, code"]

    # normalize headers
    def row_get(row: dict, key: str) -> str:
        for k, v in row.items():
            if k and k.strip().lower() == key:
                return (v or "").strip()
        return ""

    imported = 0
    skipped = 0
    errors: list[str] = []

    existing_codes_result = await db.execute(select(CertificateCode.code))
    existing_codes = {c for (c,) in existing_codes_result.all()}

    for i, raw in enumerate(reader, start=2):
        try:
            nominal = int(row_get(raw, "denomination_rub"))
            code_val = row_get(raw, "code")
            if not code_val:
                skipped += 1
                continue
            if code_val in existing_codes:
                skipped += 1
                continue
            pin = row_get(raw, "pin") or None
            variant = row_get(raw, "variant") or "spa"
            if variant not in ("spa", "ar"):
                variant = "spa"
            valid_until = None
            vu = row_get(raw, "valid_until")
            if vu:
                valid_until = date.fromisoformat(vu)
            batch_id = row_get(raw, "batch_id") or None

            denom = await get_or_create_denomination(db, variant=variant, nominal_rub=nominal)
            db.add(
                CertificateCode(
                    denomination_id=denom.id,
                    code=code_val,
                    pin=pin,
                    valid_until=valid_until,
                    batch_id=batch_id,
                    status=CodeStatus.available,
                )
            )
            existing_codes.add(code_val)
            imported += 1
        except Exception as e:
            errors.append(f"row {i}: {e}")
            skipped += 1

    await log_action(
        db,
        "csv_import",
        actor=actor,
        details={"imported": imported, "skipped": skipped, "errors": errors[:20]},
    )
    return imported, skipped, errors
