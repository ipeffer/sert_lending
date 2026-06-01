import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_admin
from app.models import AuditLog, CertificateCode, CodeStatus, Order, OrderStatus
from app.services.orders import retry_delivery
from app.schemas import ImportResult, StockRow
from app.services.audit import log_action
from app.services.certificates import import_csv, mask_code, stock_summary

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stock", response_model=list[StockRow])
async def get_stock(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> list[StockRow]:
    rows = await stock_summary(db)
    return [StockRow(**r) for r in rows]


@router.post("/import", response_model=ImportResult)
async def post_import(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(require_admin),
) -> ImportResult:
    content = await file.read()
    imported, skipped, errors = await import_csv(db, content, actor=actor)
    await db.commit()
    return ImportResult(imported=imported, skipped=skipped, errors=errors)


@router.get("/stock/export")
async def export_stock(
    mask_codes: bool = True,
    full: bool = False,
    x_export_full: str | None = Header(default=None, alias="X-Export-Full"),
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(require_admin),
):
    allow_full = full and x_export_full == "1"
    if full and not allow_full:
        raise HTTPException(status_code=400, detail="Full export requires X-Export-Full: 1")

    from app.models import Denomination

    stmt = (
        select(
            CertificateCode.code,
            CertificateCode.pin,
            CertificateCode.status,
            Denomination.variant,
            Denomination.nominal_rub,
            CertificateCode.valid_until,
            CertificateCode.batch_id,
        )
        .join(Denomination, Denomination.id == CertificateCode.denomination_id)
        .order_by(CertificateCode.id)
    )
    if mask_codes and not allow_full:
        stmt = stmt.where(CertificateCode.status != CodeStatus.sold)

    q = await db.execute(stmt)
    rows = q.all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["variant", "nominal_rub", "code", "pin", "status", "valid_until", "batch_id"]
    )
    for code, pin, status, variant, nominal, valid_until, batch_id in rows:
        out_code = mask_code(code) if (mask_codes and not allow_full) else code
        writer.writerow(
            [
                variant,
                nominal,
                out_code,
                pin or "",
                status.value if hasattr(status, "value") else status,
                valid_until.isoformat() if valid_until else "",
                batch_id or "",
            ]
        )

    if allow_full:
        await log_action(db, "full_export", actor=actor, details={"rows": len(rows)})
        await db.commit()

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=stock-export.csv"},
    )


@router.get("/orders/pending-delivery")
async def pending_delivery(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    result = await db.execute(
        select(Order).where(Order.status == OrderStatus.paid_pending_delivery).order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()
    return [
        {
            "id": str(o.id),
            "public_token": o.public_token,
            "buyer_email": o.buyer_email,
            "nominal_rub": o.nominal_rub,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in orders
    ]


@router.post("/orders/{order_id}/retry-delivery")
async def post_retry_delivery(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(require_admin),
):
    try:
        order = await retry_delivery(db, order_id)
        await log_action(db, "admin_retry_delivery", actor=actor, order_id=order_id)
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"status": "ok", "email_sent": order.email_sent_at is not None}


@router.get("/audit")
async def get_audit(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 500))
    )
    logs = result.scalars().all()
    return [
        {
            "id": l.id,
            "action": l.action,
            "actor": l.actor,
            "order_id": str(l.order_id) if l.order_id else None,
            "details": l.details,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]
