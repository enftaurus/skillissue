from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from backend.app.core.config import settings

# Async engine for application runtime
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Postgres text columns reject NUL bytes ("\x00"); a single pasted NUL used to 500 the request.
# Strip them from every string column on every model before it reaches the database.
from sqlalchemy import event, String as _String, Text as _Text  # noqa: E402
from sqlalchemy.orm import Session as _SyncSession  # noqa: E402


@event.listens_for(_SyncSession, "before_flush")
def _strip_nul_bytes(session, flush_context, instances):  # pragma: no cover - exercised via API tests
    for obj in list(session.new) + list(session.dirty):
        mapper = getattr(obj, "__mapper__", None)
        if mapper is None:
            continue
        for col in mapper.columns:
            if isinstance(col.type, (_String, _Text)):
                key = mapper.get_property_by_column(col).key
                value = getattr(obj, key, None)
                if isinstance(value, str) and "\x00" in value:
                    setattr(obj, key, value.replace("\x00", ""))
