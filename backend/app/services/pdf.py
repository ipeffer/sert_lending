import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def build_certificate_pdf(
    *,
    variant: str,
    nominal_rub: int,
    code: str,
    pin: str | None,
    valid_until: date | None,
    buyer_name: str,
) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    brand = colors.HexColor("#a38460")
    c.setFillColor(brand)
    c.rect(0, height - 40 * mm, width, 40 * mm, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    title = "Тестовая СПА продажа" if variant == "spa" else "Адмиральский разряд"
    c.drawString(25 * mm, height - 25 * mm, f"Подарочный сертификат — {title}")

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 36)
    c.drawString(25 * mm, height - 70 * mm, f"{nominal_rub:,}".replace(",", " ") + " ₽")

    c.setFont("Helvetica", 14)
    y = height - 95 * mm
    lines = [
        f"Получатель: {buyer_name}",
        f"Номер сертификата: {code}",
        f"PIN: {pin or '—'}",
        f"Действителен до: {valid_until.isoformat() if valid_until else '—'}",
        "",
        "Демонстрационный сертификат тестового стенда.",
        "Тестовая СПА продажа",
    ]
    for line in lines:
        c.drawString(25 * mm, y, line)
        y -= 8 * mm

    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(colors.grey)
    c.drawString(25 * mm, 20 * mm, "Тестовая СПА продажа · демо")

    c.showPage()
    c.save()
    return buf.getvalue()
