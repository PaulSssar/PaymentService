"""
Репозиторий для работы с Payment.
CRUD-операции: создание, поиск по id и idempotency_key.
"""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PaymentModel, PaymentStatus

logger = logging.getLogger(__name__)


class PaymentRepository:
    """Репозиторий для Payment."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payment: PaymentModel) -> PaymentModel:
        """Создаёт новый Payment."""
        self.session.add(payment)
        await self.session.flush()
        await self.session.refresh(payment)
        return payment

    async def get_by_id(self, payment_id: UUID) -> PaymentModel | None:
        """Находит Payment по id."""
        stmt = select(PaymentModel).where(PaymentModel.id == payment_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> PaymentModel | None:
        """Находит Payment по idempotency_key."""
        stmt = select(PaymentModel).where(PaymentModel.idempotency_key == key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(self, payment_id: UUID, status: PaymentStatus, processed_at: datetime | None = None) -> PaymentModel | None:
        """Обновляет статус платежа."""
        stmt = (
            select(PaymentModel)
            .where(PaymentModel.id == payment_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        payment = result.scalar_one_or_none()
        if payment:
            payment.status = status
            if processed_at is not None:
                payment.processed_at = processed_at
            await self.session.flush()
            logger.info("Payment status updated, id=%s, status=%s", payment_id, status)
        return payment
