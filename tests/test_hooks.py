from panel_hermes_plugin._config import PluginConfig
from panel_hermes_plugin._hooks import HookRuntime
from panel_hermes_plugin._sampler import TraceSampler


class StubIngest:
    def __init__(self):
        self.items = []

    def enqueue_nowait(self, kind, payload):
        self.items.append((kind, payload))
        return True


def cfg():
    return PluginConfig(
        enabled=True,
        base_url="https://panel",
        site_key="pk",
        site_secret="sk",
        pool="hermes-traces",
        sample_rate=1.0,
        dry_run=False,
        failure_threshold=5,
        cooldown_seconds=60,
        exclude_tools=("read_file",),
        scrubber_mode="off",
        scrubber_url=None,
        scrubber_jwt_secret=None,
        novelty_window=100,
        queue_size=10,
    )


def test_excluded_tool_not_ingested():
    ingest = StubIngest()
    rt = HookRuntime(config=cfg(), sampler=TraceSampler(sample_rate=1.0), ingest=ingest)
    rt.post_tool_call(tool_name="read_file", args={}, result={})
    assert ingest.items == []


def test_trace_and_unit_ingested():
    ingest = StubIngest()
    rt = HookRuntime(config=cfg(), sampler=TraceSampler(sample_rate=1.0), ingest=ingest)
    rt.pre_api_request(conversation_history=[{"role": "user", "content": "hi"}])
    rt.post_api_request(assistant_response="hello")
    rt.post_tool_call(tool_name="write_file", args={"a": 1}, result={"ok": True})
    kinds = [k for k, _ in ingest.items]
    assert "trace" in kinds
    assert "unit" in kinds
