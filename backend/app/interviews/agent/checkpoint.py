import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.memory import MemorySaver
from backend.app.core.config import settings
from backend.app.core.logging import logger

_memory_saver = MemorySaver()

@asynccontextmanager
async def get_interview_checkpointer() -> AsyncIterator[BaseCheckpointSaver]:
    """
    Provides a PostgreSQL-backed checkpointer for persistent state recovery.
    Falls back gracefully to an in-memory checkpointer in isolated test suites
    where the live PostgreSQL database is not running.
    """
    try:
        # Use sync PostgreSQL connection URL format required by psycopg3 in AsyncPostgresSaver
        conn_str = settings.DATABASE_URL_SYNC
        async with AsyncPostgresSaver.from_conn_string(conn_str) as saver:
            yield saver
    except Exception as e:
        logger.warning(
            f"Failed to connect to PostgreSQL checkpointer: {e}. Falling back to in-memory checkpointer."
        )
        yield _memory_saver
