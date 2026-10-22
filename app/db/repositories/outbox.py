import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import OutboxModel, OutboxStatus

logger = logging.getLogger(__name__)


class OutboxRepository:
    """Репозиторий для Outbox."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, outbox: OutboxModel) -> OutboxModel:
        """Создаёт новую outbox-запись."""
        self.session.add(outbox)
        await self.session.flush()
        await self.session.refresh(outbox)
        return outbox

    async def get_pending_batch(self, batch_size: int | None = None) -> list[OutboxModel]:
        """
        Выбирает пакет pending-записей с FOR UPDATE SKIP LOCKED.
        Не блокирует записи, уже захваченные другими транзакциями.
        """
        size = batch_size or settings.OUTBOX_BATCH_SIZE
        now = datetime.now(timezone.utc)
        stmt = (
            select(OutboxModel)
            .where(
                OutboxModel.status == OutboxStatus.PENDING,
                OutboxModel.created_at <= now,
            )
            .order_by(OutboxModel.created_at)
            .limit(size)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)
        records = list(result.scalars().all())
        logger.debug("Fetched %d pending outbox records", len(records))
        return records

    async def mark_published(self, outbox_ids: list[UUID]) -> int:
        """Помечает outbox-записи как published."""
        if not outbox_ids:
            return 0

        stmt = (
            update(OutboxModel)
            .where(OutboxModel.id.in_(outbox_ids))
            .values(
                status=OutboxStatus.PUBLISHED,
                published_at=datetime.now(timezone.utc),
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        logger.info("Marked %d outbox records as published", result.rowcount)
        return result.rowcount
