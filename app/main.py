"""
FastAPI приложение с lifespan-менеджером.
Собирает все роуты, настраивает middleware и lifecycle.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config
from alembic.command import upgrade
from fastapi import FastAPI

from app.api.v1 import payments
from app.core.config import settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление lifecycle приложения."""
    # Startup: применяем миграции Alembic (в потоке, чтобы не блокировать event loop)
    logger.info("Running Alembic migrations...")
    alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    await asyncio.to_thread(upgrade, alembic_cfg, "head")
    logger.info("Migrations applied successfully")

    yield

    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title="Payment Service",
    description="Микросервис для обработки платежей с outbox-паттерном",
    version="0.1.0",
    lifespan=lifespan,
)

# Регистрируем роуты
app.include_router(payments.router, prefix=settings.API_PREFIX)


@app.get("/health")
async def health_check():
    """Health-check endpoint."""
    return {"status": "ok"}
