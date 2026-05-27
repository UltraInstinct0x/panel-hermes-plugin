import asyncio

import pytest

from panel_hermes_plugin._config import PluginConfig
from panel_hermes_plugin._ingest import IngestWorker


class DummyClient:
    def __init__(self):
        self.units = []
        self.traces = []
        self.poll = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def ingest_unit(self, type_name, payload, pool="public"):
        self.units.append((type_name, payload, pool))
        return {"ok": True}

    async def ingest_trace(self, source_agent, blob, trace_id=None, extra_headers=None):
        self.traces.append((source_agent, blob, trace_id, extra_headers))
        return {"trace_id": "tr_1"}

    async def get_trace(self, trace_id):
        self.poll.append(trace_id)
        return {"status": "done"}


def make_cfg(dry_run=False):
    return PluginConfig(
        enabled=True,
        base_url="https://panel",
        site_key="pk",
        site_secret="sk",
        pool="hermes-traces",
        sample_rate=0.1,
        dry_run=dry_run,
        failure_threshold=2,
        cooldown_seconds=1,
        exclude_tools=(),
        scrubber_mode="off",
        scrubber_url=None,
        scrubber_jwt_secret=None,
        novelty_window=100,
        queue_size=2,
    )


@pytest.mark.asyncio
async def test_dry_run_no_post():
    client = DummyClient()
    worker = IngestWorker(config=make_cfg(dry_run=True), client_factory=lambda: client)
    worker.start()
    worker.enqueue_nowait("unit", {"type": "process_tool_call_rating", "payload": {}, "pool": "p"})
    await worker.flush()
    await worker.stop()
    assert client.units == []


@pytest.mark.asyncio
async def test_circuit_breaker_open_close():
    class FailingClient(DummyClient):
        async def ingest_unit(self, type_name, payload, pool="public"):
            raise RuntimeError("boom")

    worker = IngestWorker(config=make_cfg(), client_factory=lambda: FailingClient())
    worker.start()
    worker.enqueue_nowait("unit", {"type": "process_tool_call_rating", "payload": {}, "pool": "p"})
    worker.enqueue_nowait("unit", {"type": "process_tool_call_rating", "payload": {}, "pool": "p"})
    await asyncio.sleep(0.2)
    assert worker.breaker.allow() is False
    await asyncio.sleep(1.1)
    assert worker.breaker.allow() is True
    await worker.stop()
