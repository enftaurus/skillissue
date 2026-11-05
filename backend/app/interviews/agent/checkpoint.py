import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
from typing import AsyncIterator, Optional
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.memory import MemorySaver
from backend.app.core.config import settings
from backend.app.core.errors import AppException
from backend.app.core.logging import logger

_setup_done = False
_setup_lock = asyncio.Lock()
_memory_fallback: Optional[MemorySaver] = None


@asynccontextmanager
async def get_interview_checkpointer() -> AsyncIterator[BaseCheckpointSaver]:
    """
    Provides a PostgreSQL-backed checkpointer for persistent state recovery.
    In production, failure to connect fails closed. In development/testing it falls back
    to a process-wide in-memory checkpointer.

    Only *connecting* is guarded. Exceptions raised by the caller's body (LLM errors,
    timeouts, content filters) propagate unchanged. They are not checkpointer failures.
    """
    global _setup_done, _memory_fallback
    async with AsyncExitStack() as stack:
        saver: Optional[BaseCheckpointSaver] = None
        try:
            saver = await stack.enter_async_context(
                AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL_SYNC)
            )
            if not _setup_done and hasattr(saver, "setup"):
                async with _setup_lock:
                    if not _setup_done:
                        await saver.setup()
                        _setup_done = True
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
            if _memory_fallback is None:
                _memory_fallback = MemorySaver()
            saver = _memory_fallback

        yield saver
