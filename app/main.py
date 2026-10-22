"""
FastAPI приложение с lifespan-менеджером.
Собирает все роуты, настраивает middleware и lifecycle.
"""

import logging
from contextlib import asynccontextmanager

from alembic.config import Config
from alembic.command import upgrade
from fastapi import FastAPI

from app.api.v1 import payments
from app.core.config import settings

log_level = getattr(logging, str(settings.LOG_LEVEL).upper(), logging.INFO)

# Настраиваем форматтер
formatter = logging.Formatter(
    "%(asctime)s %(name)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление lifecycle приложения."""
    # Startup: применяем миграции Alembic
    logger.info("Running Alembic migrations...")
    alembic_cfg = Config("alembic.ini")
    upgrade(alembic_cfg, "head")
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

app.include_router(payments.router, prefix=settings.API_PREFIX)


@app.get("/health")
async def health_check():
    """Health-check endpoint."""
    return {"status": "ok"}
