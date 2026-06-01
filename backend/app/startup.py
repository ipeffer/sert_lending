import logging
from pathlib import Path

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import CertificateCode
from app.services.certificates import import_csv

logger = logging.getLogger(__name__)

def _sample_csv_path() -> Path:
    candidates = [
        Path("/samples/certificates.sample.csv"),
        Path(__file__).resolve().parents[2] / "samples" / "certificates.sample.csv",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return candidates[-1]


SAMPLE_CSV = _sample_csv_path()


async def seed_if_empty() -> None:
    async with SessionLocal() as db:
        count = (await db.execute(select(func.count(CertificateCode.id)))).scalar_one()
        if count and count > 0:
            logger.info("Certificate pool already has %s codes, skip seed", count)
            return

        if not SAMPLE_CSV.is_file():
            logger.warning("Sample CSV not found at %s", SAMPLE_CSV)
            return

        content = SAMPLE_CSV.read_bytes()
        imported, skipped, errors = await import_csv(db, content, actor="startup")
        await db.commit()
        logger.info("Seeded %s certificate codes (skipped=%s)", imported, skipped)
        if errors:
            logger.warning("Seed errors: %s", errors[:5])
