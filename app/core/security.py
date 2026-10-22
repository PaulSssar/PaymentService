"""
Зависимость FastAPI для проверки X-API-Key заголовка.
Возвращает True, если ключ валиден, иначе 401.
"""

from fastapi import Header, HTTPException, status

from app.core.config import settings


async def validate_api_key(x_api_key: str = Header(...)) -> bool:
    """Проверяет X-API-Key заголовок против конфига."""
    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return True
