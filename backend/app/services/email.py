import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import get_settings

logger = logging.getLogger(__name__)


async def send_certificate_email(
    *,
    to_email: str,
    buyer_name: str,
    nominal_rub: int,
    pdf_bytes: bytes,
) -> bool:
    settings = get_settings()
    if not settings.smtp_host:
        logger.warning("SMTP not configured; skipping email to %s", to_email)
        return False

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg["Subject"] = f"Ваш подарочный сертификат — Тестовая СПА продажа, {nominal_rub} ₽"
    msg.set_content(
        f"Здравствуйте, {buyer_name}!\n\n"
        f"Спасибо за покупку подарочного сертификата на {nominal_rub} ₽.\n"
        f"PDF сертификата во вложении.\n\n"
        f"Фискальный чек направляет платёжная система на указанный email.\n\n"
        f"Тестовая СПА продажа · демо-стенд"
    )
    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename="test-spa-certificate.pdf",
    )

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        start_tls=settings.smtp_use_tls,
    )
    return True
