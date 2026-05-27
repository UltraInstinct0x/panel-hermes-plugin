from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from ._config import PluginConfig

logger = logging.getLogger(__name__)


@dataclass
class CircuitBreaker:
    failure_threshold: int
    cooldown_seconds: int
    consecutive_failures: int = 0
    opened_at: float = 0.0

    def allow(self) -> bool:
        if self.opened_at <= 0:
            return True
        if (time.time() - self.opened_at) >= self.cooldown_seconds:
            self.opened_at = 0.0
            self.consecutive_failures = 0
            return True
        return False

    def record_success(self) -> None:
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.opened_at = time.time()


@dataclass
class IngestWorker:
    config: PluginConfig
    client_factory: Any
    queue: asyncio.Queue[tuple[str, dict[str, Any]]] = field(init=False)
    breaker: CircuitBreaker = field(init=False)
    _runner_task: asyncio.Task | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.queue = asyncio.Queue(maxsize=self.config.queue_size)
        self.breaker = CircuitBreaker(self.config.failure_threshold, self.config.cooldown_seconds)

    def start(self) -> None:
        if self._runner_task is None:
            self._runner_task = asyncio.create_task(self._run(), name="panel-hermes-ingest")

    async def stop(self) -> None:
        if self._runner_task is None:
            return
        self._runner_task.cancel()
        try:
            await self._runner_task
        except asyncio.CancelledError:
            pass
        self._runner_task = None

    def enqueue_nowait(self, kind: str, payload: dict[str, Any]) -> bool:
        try:
            self.queue.put_nowait((kind, payload))
            return True
        except asyncio.QueueFull:
            logger.warning("panel-hermes-plugin: queue full, dropped %s", kind)
            return False

    async def flush(self) -> None:
        await self.queue.join()

    async def _run(self) -> None:
        async with self.client_factory() as client:
            while True:
                kind, payload = await self.queue.get()
                try:
                    if not self.breaker.allow():
                        continue
                    if self.config.dry_run:
                        logger.info("panel-hermes-plugin dryRun %s: %s", kind, payload)
                        self.breaker.record_success()
                        continue
                    if kind == "unit":
                        await client.ingest_unit(
                            payload["type"], payload["payload"], pool=payload["pool"]
                        )
                    elif kind == "trace":
                        result = await client.ingest_trace(
                            payload["source_agent"],
                            payload["blob"],
                            trace_id=payload.get("trace_id"),
                        )
                        trace_id = result.get("trace_id")
                        if trace_id:
                            await self._poll_trace(client, trace_id)
                    self.breaker.record_success()
                except Exception as exc:
                    logger.warning("panel-hermes-plugin ingest failed: %s", exc)
                    self.breaker.record_failure()
                finally:
                    self.queue.task_done()

    async def _poll_trace(self, client: Any, trace_id: str, max_attempts: int = 3) -> None:
        for _ in range(max_attempts):
            status = await client.get_trace(trace_id)
            if isinstance(status, dict) and status.get("status") != "pending":
                return
            await asyncio.sleep(0.2)
