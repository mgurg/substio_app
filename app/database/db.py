from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.config import get_settings

settings = get_settings()

echo = False

engine = create_async_engine(
    settings.DB_POSTGRES_URL.unicode_string(),
    echo=echo,
    pool_pre_ping=True,
    pool_recycle=280,
)

async_session = async_sessionmaker(bind=engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


Base = declarative_base()
