"""
Pydantic v2 схемы для сериализации/валидации платежей.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaymentCreate(BaseModel):
    """Схема для создания платежа (тело запроса)."""

    amount: Decimal = Field(..., gt=0, description="Сумма платежа")
    currency: str = Field(..., pattern="^(RUB|USD|EUR)$", description="Валюта")
    description: str = Field(..., min_length=1, max_length=500, description="Описание платежа")
    metadata: dict | None = Field(default=None, description="Дополнительные метаданные")
    webhook_url: str = Field(..., description="URL для webhook-уведомления")


class PaymentResponse(BaseModel):
    """Схема ответа с данными платежа."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: Decimal
    currency: str
    description: str
    metadata: dict | None
    status: str
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None
