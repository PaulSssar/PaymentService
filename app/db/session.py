"""
Асинхронный engine и sessionmaker для SQLAlchemy 2.0.
Использует asyncpg для PostgreSQL.
"""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def get_session():
    """Generator-зависимость для FastAPI: открывает сессию на запрос."""
    async with async_session_factory() as session:
        yield session
