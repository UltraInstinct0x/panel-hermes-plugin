from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from ._config import PluginConfig
from ._ingest import IngestWorker
from ._sampler import TraceSampler


@dataclass
class HookRuntime:
    config: PluginConfig
    sampler: TraceSampler
    ingest: IngestWorker
    tool_started: dict[str, float] = field(default_factory=dict)
    messages: list[dict[str, Any]] = field(default_factory=list)

    def pre_api_request(self, **kwargs: Any) -> None:
        history = kwargs.get("conversation_history") or kwargs.get("messages")
        if isinstance(history, list):
            self.messages = [m for m in history if isinstance(m, dict)]

    def post_api_request(self, **kwargs: Any) -> None:
        assistant = kwargs.get("assistant_response")
        if isinstance(assistant, str) and assistant:
            self.messages.append({"role": "assistant", "content": assistant})
        sampled, reason = self.sampler.should_sample_trace(
            self.messages, force_error=bool(kwargs.get("error"))
        )
        if not sampled:
            return
        self.ingest.enqueue_nowait(
            "trace",
            {
                "source_agent": "hermes",
                "blob": {
                    "messages": self.messages,
                    "reason": reason,
                    "plugin_version": "0.1.0",
                },
            },
        )

    def pre_llm_call(self, **_: Any) -> None:
        return

    def post_llm_call(self, **_: Any) -> None:
        return

    def pre_tool_call(self, **kwargs: Any) -> None:
        tool_call_id = str(kwargs.get("tool_call_id") or "")
        if tool_call_id:
            self.tool_started[tool_call_id] = time.perf_counter()

    def post_tool_call(self, **kwargs: Any) -> None:
        tool_name = str(kwargs.get("tool_name") or "")
        if tool_name in self.config.exclude_tools:
            return
        tool_call_id = str(kwargs.get("tool_call_id") or "")
        started = self.tool_started.pop(tool_call_id, time.perf_counter())
        duration_ms = int((time.perf_counter() - started) * 1000)

        payload = {
            "tool": tool_name,
            "args": kwargs.get("args"),
            "result": kwargs.get("result"),
            "duration_ms": duration_ms,
            "error": bool(kwargs.get("error")),
        }
        sampled, _ = self.sampler.should_sample_unit(tool_name, payload)
        if not sampled:
            return
        self.ingest.enqueue_nowait(
            "unit",
            {
                "type": "process_tool_call_rating",
                "pool": self.config.pool,
                "payload": payload,
            },
        )
