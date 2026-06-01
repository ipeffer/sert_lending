import ipaddress

from fastapi import HTTPException, Request

from app.config import get_settings


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""


def verify_yookassa_ip(request: Request) -> None:
    settings = get_settings()
    raw = settings.yookassa_webhook_ips.strip()
    if not raw:
        return

    client = _client_ip(request)
    if not client:
        raise HTTPException(status_code=403, detail="Cannot determine client IP")

    try:
        addr = ipaddress.ip_address(client)
    except ValueError as e:
        raise HTTPException(status_code=403, detail="Invalid client IP") from e

    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            if "/" in part:
                if addr in ipaddress.ip_network(part, strict=False):
                    return
            elif client == part:
                return
        except ValueError:
            continue

    raise HTTPException(status_code=403, detail="Webhook IP not allowed")
