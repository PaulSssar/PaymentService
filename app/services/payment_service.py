"""
Сервис для создания платежа с идемпотентностью и outbox-паттерном.
Создаёт Payment и Outbox-запись в одной транзакции.
"""

import logging
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Currency, OutboxStatus, PaymentStatus, OutboxModel, PaymentModel
from app.db.repositories.outbox import OutboxRepository
from app.db.repositories.payment import PaymentRepository
from app.schemas.payment import PaymentCreate

logger = logging.getLogger(__name__)


class PaymentService:
    """Сервис для бизнес-логики платежей."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.payment_repo = PaymentRepository(session)
        self.outbox_repo = OutboxRepository(session)

    async def create_payment(self, data: PaymentCreate, idempotency_key: str) -> PaymentModel:
        """Создаёт платёж с идемпотентностью."""
        # Проверяем идемпотентность
        existing = await self.payment_repo.get_by_idempotency_key(idempotency_key)
        if existing:
            logger.info(
                "Idempotency key matched, returning existing payment, id=%s",
                existing.id,
            )
            return existing

        # Создаём Payment
        payment = PaymentModel(
            id=uuid4(),
            amount=data.amount,
            currency=Currency(data.currency),
            description=data.description,
            extra_data=data.extra_data,
            idempotency_key=idempotency_key,
            webhook_url=data.webhook_url,
            status=PaymentStatus.PENDING,
        )
        payment = await self.payment_repo.create(payment)
        logger.info(
            "Payment created, id=%s, amount=%s, currency=%s",
            payment.id, payment.amount, payment.currency,
        )

        # Создаём Outbox-запись
        outbox = OutboxModel(
            id=uuid4(),
            event_type="payment.created",
            payload={
                "payment_id": str(payment.id),
                "amount": str(payment.amount),
                "currency": payment.currency,
                "webhook_url": payment.webhook_url,
            },
            status=OutboxStatus.PENDING,
        )
        await self.outbox_repo.create(outbox)
        logger.info("Outbox record created for payment %s", payment.id)

        return payment
