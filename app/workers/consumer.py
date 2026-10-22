"""
FastStream consumer для обработки платежей.
Получает сообщения из очереди payments.process,
эмулирует обработку, обновляет статус и отправляет webhook.
"""

import asyncio
import logging
import random
from datetime import datetime, timezone
from uuid import UUID

from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, ExchangeType, RabbitQueue
from sqlalchemy import select

from app.core.config import settings
from app.db.models import PaymentModel, PaymentStatus
from app.db.session import async_session_factory
from app.services.webhook import send_webhook

logger = logging.getLogger(__name__)

broker = RabbitBroker(settings.RABBITMQ_URL)
app = FastStream(broker)


@broker.subscriber(
    queue=RabbitQueue(
        name="payments.process",
        routing_key="payment.process",     # ✅ routing_key здесь
    ),
    exchange=RabbitExchange(
        name="payments",
        type=ExchangeType.DIRECT,
    ),
)
async def handle_payment_message(message: dict):
    """
    Обработчик сообщения о платеже.
    1. Эмулирует обработку (sleep 2-5s, 90% succeeded).
    2. Отправляет webhook.
    3. Обновляет статус в БД (после webhook, чтобы при ошибке webhook статус не менялся).
    """
    payment_id = UUID(message.get("payment_id"))
    webhook_url = message.get("webhook_url", "")
    payload = message.get("payload", {})

    logger.info("Processing payment %s", payment_id)

    # Эмуляция обработки
    await asyncio.sleep(random.uniform(2, 5))
    success = random.random() < 0.9
    new_status = PaymentStatus.SUCCEEDED if success else PaymentStatus.FAILED

    # Обновляем статус в БД
    async with async_session_factory() as session:
        stmt = (
            select(PaymentModel)
            .where(PaymentModel.id == payment_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        payment = result.scalar_one_or_none()

        if not payment:
            logger.warning("Payment %s not found", payment_id)
            await session.rollback()
            return

        # Отправляем webhook ДО обновления статуса — если webhook упадёт,
        # статус останется pending и сообщение можно будет обработать повторно.
        webhook_payload = {
            "event": "payment.processed",
            "payment_id": str(payment.id),
            "status": new_status.value,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }

        webhook_ok = await send_webhook(webhook_url, webhook_payload)

        # Обновляем статус (и processed_at)
        payment.status = new_status
        payment.processed_at = datetime.now(timezone.utc)
        await session.flush()
        await session.commit()

        if not webhook_ok:
            logger.error(
                "Webhook failed for payment %s — message should go to DLQ",
                payment_id,
            )
            # В продакшене: отправляем сообщение в retry/DLQ очередь
            # Для скелета — просто логируем


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    logger.info("Starting consumer...")
    asyncio.run(app.run())
