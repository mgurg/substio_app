from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_settings

settings = get_settings()

echo = False

print(settings.DB_POSTGRES_URL.unicode_string())

engine = create_async_engine(
    settings.DB_POSTGRES_URL.unicode_string(),
    echo=echo,
    pool_pre_ping=True,
    pool_recycle=280,
)

SessionLocal = async_sessionmaker(engine, autocommit=False, autoflush=False)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# metadata = sa.MetaData(schema="tenant")
Base = declarative_base()
