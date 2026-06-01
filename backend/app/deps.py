import secrets

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db

security = HTTPBasic()


async def require_admin(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> str:
    settings = get_settings()
    if settings.admin_ips:
        client = request.client.host if request.client else ""
        if client not in settings.admin_ips:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="IP not allowed")

    user_ok = secrets.compare_digest(credentials.username, settings.admin_username)
    pass_ok = secrets.compare_digest(credentials.password, settings.admin_password)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
