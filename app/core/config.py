"""
Конфигурация приложения через pydantic-settings.
Читает переменные окружения или .env файл.
"""

from enum import StrEnum
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # игнорируем лишние переменные из .env
    )

    API_KEY: str = Field(..., description="Shared API key for X-API-Key header validation")
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # PostgreSQL
    POSTGRES_USER: str = "payment_user"
    POSTGRES_PASSWORD: str = "payment_pass"
    POSTGRES_DB: str = "payment_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = Field(
        default="",
        description="PostgreSQL async connection url (generated from POSTGRES_*)",
    )
    DB_POOL_SIZE: int = Field(default=5, description="Connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Max overflow connections")

    # RabbitMQ
    RABBITMQ_DEFAULT_USER: str = "guest"
    RABBITMQ_DEFAULT_PASS: str = "guest"
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_URL: str = Field(
        default="",
        description="RabbitMQ connection URL (generated from RABBITMQ_*)",
    )

    WEBHOOK_TIMEOUT: int = Field(default=10, description="Webhook request timeout in seconds")
    WEBHOOK_MAX_RETRIES: int = Field(default=3, description="Max webhook retry attempts")

    LOG_LEVEL: str = Field(default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")

    OUTBOX_POLL_INTERVAL: float = Field(default=2.0, description="Seconds between outbox polls")
    OUTBOX_BATCH_SIZE: int = Field(default=50, description="Max records per outbox poll")

    @model_validator(mode="before")
    @classmethod
    def generate_urls(cls, data):
        """Генерирует DATABASE_URL и RABBITMQ_URL из переменных."""
        if not isinstance(data, dict):
            return data

        pg_user = data.get("POSTGRES_USER", "payment_user")
        pg_pass = data.get("POSTGRES_PASSWORD", "payment_pass")
        pg_host = data.get("POSTGRES_HOST", "localhost")
        pg_port = data.get("POSTGRES_PORT", 5432)
        pg_db = data.get("POSTGRES_DB", "payment_db")

        if not data.get("DATABASE_URL"):
            data["DATABASE_URL"] = (
                f"postgresql+asyncpg://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
            )

        rmq_user = data.get("RABBITMQ_DEFAULT_USER", "guest")
        rmq_pass = data.get("RABBITMQ_DEFAULT_PASS", "guest")
        rmq_host = data.get("RABBITMQ_HOST", "localhost")
        rmq_port = data.get("RABBITMQ_PORT", 5672)

        if not data.get("RABBITMQ_URL"):
            data["RABBITMQ_URL"] = f"amqp://{rmq_user}:{rmq_pass}@{rmq_host}:{rmq_port}/"

        return data


settings = Settings()
