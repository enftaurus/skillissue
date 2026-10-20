from contextlib import asynccontextmanager
from typing import AsyncIterator
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.memory import MemorySaver
from backend.app.core.config import settings
from backend.app.core.errors import AppException
from backend.app.core.logging import logger

@asynccontextmanager
async def get_interview_checkpointer() -> AsyncIterator[BaseCheckpointSaver]:
    """
    Provides a PostgreSQL-backed checkpointer for persistent state recovery.
    In production, failure to connect to PostgreSQL checkpointer fails closed.
    In development/testing, falls back cleanly to an in-memory checkpointer.
    """
    try:
        conn_str = settings.DATABASE_URL_SYNC
        async with AsyncPostgresSaver.from_conn_string(conn_str) as saver:
            if hasattr(saver, "setup"):
                await saver.setup()
            yield saver
    except AppException:
        raise
    except Exception as e:
        if settings.ENVIRONMENT.lower() == "production":
            logger.error(
                f"CRITICAL OPERATIONAL ALERT: Failed to connect to durable PostgreSQL checkpointer in production: {e}. Failing closed."
            )
            raise AppException(
                "Durable interview checkpointer unavailable in production environment",
                code="CHECKPOINT_PERSISTENCE_FAILED",
                status_code=503,
            )
        logger.warning(
            f"Failed to connect to PostgreSQL checkpointer: {e}. Falling back to in-memory checkpointer for dev/test."
        )
        yield MemorySaver()
