import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import Base, engine
from app.routers import admin, public, webhooks
from app.services.certificates import release_expired_reservations
from app.startup import seed_if_empty
from app.db import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _reservation_loop() -> None:
    while True:
        try:
            async with SessionLocal() as db:
                n = await release_expired_reservations(db)
                await db.commit()
                if n:
                    logger.info("Released %s expired reservations", n)
        except Exception:
            logger.exception("Reservation cleanup failed")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_if_empty()
    task = asyncio.create_task(_reservation_loop())
    yield
    task.cancel()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Тестовая СПА продажа API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(public.router)
    app.include_router(admin.router)
    app.include_router(webhooks.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
