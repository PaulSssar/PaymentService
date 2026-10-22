"""
Сервис для отправки webhook с retry-логикой.
3 попытки с exponential backoff.
"""

import asyncio
import logging
from typing import Any

import aiohttp

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_webhook(
    webhook_url: str,
    payload: dict[str, Any],
    max_retries: int | None = None,
) -> bool:
    """
    Отправляет webhook с retry (exponential backoff).

    Args:
        webhook_url: URL для отправки.
        payload: Тело webhook.
        max_retries: Максимум попыток (по умолчанию из конфига).

    Returns:
        True если успешно, False если все попытки исчерпаны.
    """
    retries = max_retries or settings.WEBHOOK_MAX_RETRIES
    timeout = aiohttp.ClientTimeout(total=settings.WEBHOOK_TIMEOUT)

    for attempt in range(retries + 1):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as resp:
                    if 200 <= resp.status < 300:
                        logger.info("Webhook sent successfully to %s (attempt %d)", webhook_url, attempt + 1)
                        return True
                    else:
                        logger.warning(
                            "Webhook returned status %d (attempt %d)",
                            resp.status,
                            attempt + 1,
                        )
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning("Webhook request failed (attempt %d): %s", attempt + 1, e)

        # Exponential backoff: 1s, 2s, 4s...
        if attempt < retries:
            backoff = min(2 ** attempt, 10)  # cap at 10s
            logger.info("Retrying webhook in %ds...", backoff)
            await asyncio.sleep(backoff)

    logger.error("Webhook failed after %d attempts to %s", retries + 1, webhook_url)
    return False
