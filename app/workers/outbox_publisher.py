"""
Outbox publisher — фоновый воркер.
Раз в N секунд читает pending-записи из outbox,
публикует в RabbitMQ и помечает как published.
Использует FOR UPDATE SKIP LOCKED для избежания гонок.
"""

import asyncio
import logging

from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, ExchangeType, RabbitQueue, RabbitQueue
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.repositories.outbox import OutboxRepository
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)

broker = RabbitBroker(settings.RABBITMQ_URL)
app = FastStream(broker)


async def publish_outbox_messages(session: AsyncSession) -> int:
    """Публикует pending outbox-записи в RabbitMQ."""
    repo = OutboxRepository(session)
    records = await repo.get_pending_batch()

    if not records:
        return 0

    logger.info("Publishing %d outbox records", len(records))
    await broker.declare_exchange(
        RabbitExchange("payments", type=ExchangeType.DIRECT),
    )
    queue = RabbitQueue("payments.process", routing_key="payment.process")
    await broker.declare_queue(queue)

    for record in records:
        await broker.publish(
            {
                "payment_id": str(record.payload.get("payment_id")),
                "webhook_url": str(record.payload.get("webhook_url", "")),
                "payload": record.payload,
            },
            exchange="payments",
            routing_key="payment.process",
        )
        logger.info(
            "Published outbox event %s for payment %s",
            record.id,
            record.payload.get("payment_id"),
        )

    outbox_ids = [r.id for r in records]
    await repo.mark_published(outbox_ids)
    await session.commit()

    logger.info("Published %d outbox records", len(records))
    return len(records)


async def run_outbox_publisher() -> None:
    """Основной цикл публикации outbox-записей."""
    logger.info("Starting outbox publisher (poll interval: %ss)", settings.OUTBOX_POLL_INTERVAL)

    await broker.connect()
    logger.info("Connected to RabbitMQ")

    try:
        while True:
            try:
                async with async_session_factory() as session:
                    count = await publish_outbox_messages(session)
                    if count == 0:
                        await asyncio.sleep(settings.OUTBOX_POLL_INTERVAL)
            except Exception:
                logger.exception("Error in outbox publisher cycle")
                await asyncio.sleep(settings.OUTBOX_POLL_INTERVAL)
    finally:
        await broker.close()
        logger.info("Disconnected from RabbitMQ")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    asyncio.run(run_outbox_publisher())
