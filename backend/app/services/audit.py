import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def log_action(
    db: AsyncSession,
    action: str,
    *,
    actor: str = "system",
    order_id: uuid.UUID | None = None,
    details: dict[str, Any] | str | None = None,
) -> None:
    payload = details
    if isinstance(details, dict):
        payload = json.dumps(details, ensure_ascii=False)
    db.add(
        AuditLog(
            action=action,
            actor=actor,
            order_id=order_id,
            details=payload,
        )
    )
