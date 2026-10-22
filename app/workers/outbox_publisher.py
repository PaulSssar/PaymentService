"""
Outbox publisher — фоновый воркер.
Раз в N секунд читает pending-записи из outbox,
публикует в RabbitMQ и помечает как published.
Использует FOR UPDATE SKIP LOCKED для избежания гонок.
"""

import asyncio
import logging

from faststream import FastStream
from faststream.rabbit import RabbitBroker, ExchangeType, RabbitExchange
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.repositories.outbox import OutboxRepository
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)

broker = RabbitBroker(settings.RABBITMQ_URL)
app = FastStream(broker)

async def publish_outbox_messages(session: AsyncSession) -> int:
    """
    Публикует pending outbox-записи в RabbitMQ.
    Возвращает количество опубликованных записей.
    """
    repo = OutboxRepository(session)
    records = await repo.get_pending_batch()

    if not records:
        return 0

    exchange = RabbitExchange("payments", type=ExchangeType.DIRECT)

    for record in records:
        await broker.publish(
            {
                "payment_id": str(record.payload.get("payment_id")),
                "webhook_url": str(record.payload.get("webhook_url", "")),
                "payload": record.payload,
            },
            exchange=exchange,
            routing_key="payment.process",
        )
        logger.info(
            "Published outbox event %s for payment %s",
            record.id,
            record.payload.get("payment_id"),
        )

    # Помечаем как published
    outbox_ids = [r.id for r in records]
    await repo.mark_published(outbox_ids)
    await session.commit()

    logger.info("Published %d outbox records", len(records))
    return len(records)


async def run_outbox_publisher() -> None:
    """Основной цикл публикации outbox-записей."""
    logger.info("Starting outbox publisher (poll interval: %ss)", settings.OUTBOX_POLL_INTERVAL)

    while True:
        try:
            async with async_session_factory() as session:
                count = await publish_outbox_messages(session)
                if count == 0:
                    await asyncio.sleep(settings.OUTBOX_POLL_INTERVAL)
        except Exception:
            logger.exception("Error in outbox publisher cycle")
            await asyncio.sleep(settings.OUTBOX_POLL_INTERVAL)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    asyncio.run(run_outbox_publisher())
