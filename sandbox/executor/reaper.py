import asyncio
import logging
import time
from typing import Optional
import docker

logger = logging.getLogger("sandbox.reaper")

class SandboxReaper:
    def __init__(self, interval_seconds: int = 60, max_age_seconds: int = 300):
        self.interval = interval_seconds
        self.max_age = max_age_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def reap_stale_containers(self):
        try:
            client = docker.from_env()
            containers = client.containers.list(
                all=True,
                filters={"label": "skillissue.sandbox=1"}
            )
            now = time.time()
            reaped = 0
            for c in containers:
                try:
                    created_at_str = c.attrs.get("Created", "")
                    # Check age from State.StartedAt or Created
                    # Alternatively, if container status is dead/exited or older than max_age
                    status = c.status
                    if status in ("exited", "dead"):
                        c.remove(force=True)
                        reaped += 1
                        continue

                    # If still running but older than max_age
                    c.reload()
                    started_at = c.attrs.get("State", {}).get("StartedAt", "")
                    # If older than max_age, kill and remove
                    c.remove(force=True)
                    reaped += 1
                except Exception as ex:
                    logger.warning(f"Failed to reap container {c.id}: {ex}")

            if reaped > 0:
                logger.info(f"Reaped {reaped} stale sandbox containers")
        except Exception as e:
            logger.warning(f"Sandbox reaper cycle encountered error: {e}")

    async def _loop(self):
        logger.info("Sandbox reaper background service started")
        # Run on startup
        self.reap_stale_containers()
        while self._running:
            try:
                await asyncio.sleep(self.interval)
                self.reap_stale_containers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reaper loop error: {e}")

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._loop())

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
