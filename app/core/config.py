"""
Конфигурация приложения через pydantic-settings.
Читает переменные окружения или .env файл.
"""

from enum import StrEnum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    API_KEY: str = Field(..., description="Shared API key for X-API-Key header validation")
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    DATABASE_URL: str = Field(
        ...,
        description="PostgreSQL async connection url (postgresql+asyncpg://user:pass@host:port/db)",
    )
    DB_POOL_SIZE: int = Field(default=5, description="Connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Max overflow connections")

    RABBITMQ_URL: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="RabbitMQ connection URL",
    )

    WEBHOOK_TIMEOUT: int = Field(default=10, description="Webhook request timeout in seconds")
    WEBHOOK_MAX_RETRIES: int = Field(default=3, description="Max webhook retry attempts")

    LOG_LEVEL: LogLevel = LogLevel.INFO

    OUTBOX_POLL_INTERVAL: float = Field(default=2.0, description="Seconds between outbox polls")
    OUTBOX_BATCH_SIZE: int = Field(default=50, description="Max records per outbox poll")


settings = Settings()
