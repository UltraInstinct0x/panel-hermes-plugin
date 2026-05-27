from __future__ import annotations

import hashlib
import random
from collections import deque
from dataclasses import dataclass, field


def _stable_hash(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _tool_or_msg_text(messages: list[dict]) -> str:
    chunks: list[str] = []
    for m in messages[-8:]:
        content = m.get("content")
        if isinstance(content, str):
            chunks.append(content)
        parts = m.get("parts")
        if isinstance(parts, list):
            for p in parts:
                text = p.get("text") if isinstance(p, dict) else None
                if isinstance(text, str):
                    chunks.append(text)
    return "\n".join(chunks).strip()


def has_error(payload: dict) -> bool:
    if payload.get("error"):
        return True
    result = payload.get("result")
    if isinstance(result, dict) and result.get("error"):
        return True
    return False


@dataclass
class TraceSampler:
    sample_rate: float
    novelty_window: int = 100
    rng: random.Random = field(default_factory=random.Random)
    _recent_hashes: deque[str] = field(default_factory=lambda: deque(maxlen=100))

    def __post_init__(self) -> None:
        self._recent_hashes = deque(maxlen=self.novelty_window)

    def should_sample_trace(
        self, messages: list[dict], *, force_error: bool = False
    ) -> tuple[bool, str]:
        if force_error:
            return True, "error"
        payload = _tool_or_msg_text(messages)
        digest = _stable_hash(payload) if payload else ""
        if digest and digest not in self._recent_hashes:
            self._recent_hashes.append(digest)
            return True, "novelty"
        if self.rng.random() < self.sample_rate:
            return True, "sample"
        return False, "baseline"

    def should_sample_unit(self, tool_name: str, payload: dict) -> tuple[bool, str]:
        if has_error(payload):
            return True, "error"
        if not tool_name:
            return self.rng.random() < self.sample_rate, "sample"
        digest = _stable_hash(f"{tool_name}:{payload}")
        if digest not in self._recent_hashes:
            self._recent_hashes.append(digest)
            return True, "novelty"
        if self.rng.random() < self.sample_rate:
            return True, "sample"
        return False, "baseline"
