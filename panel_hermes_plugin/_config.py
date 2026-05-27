from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    value = _env(name)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name, str(default)))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class PluginConfig:
    enabled: bool
    base_url: str
    site_key: str
    site_secret: str
    pool: str
    sample_rate: float
    dry_run: bool
    failure_threshold: int
    cooldown_seconds: int
    exclude_tools: tuple[str, ...]
    scrubber_mode: str
    scrubber_url: str | None
    scrubber_jwt_secret: str | None
    novelty_window: int
    queue_size: int


def resolve_config() -> PluginConfig:
    base_url = _env("PANEL_BASE_URL")
    site_key = _env("PANEL_SITE_KEY")
    site_secret = _env("PANEL_SITE_SECRET")
    enabled = bool(base_url and site_key and site_secret)

    sample_rate = _env_float("PANEL_HERMES_SAMPLE_RATE", 0.1)
    if sample_rate < 0:
        sample_rate = 0.0
    if sample_rate > 1:
        sample_rate = 1.0

    mode = _env("PANEL_HERMES_SCRUBBER_MODE", "off").lower()
    if mode not in {"off", "self-sign", "proxy"}:
        mode = "off"

    exclude = tuple(
        t.strip()
        for t in _env(
            "PANEL_HERMES_EXCLUDE_TOOLS",
            "read_file,search_files,browser_snapshot",
        ).split(",")
        if t.strip()
    )

    return PluginConfig(
        enabled=enabled,
        base_url=base_url,
        site_key=site_key,
        site_secret=site_secret,
        pool=_env("PANEL_HERMES_POOL", "hermes-traces"),
        sample_rate=sample_rate,
        dry_run=_env_bool("PANEL_HERMES_DRY_RUN", False),
        failure_threshold=max(1, _env_int("PANEL_HERMES_FAILURE_THRESHOLD", 5)),
        cooldown_seconds=max(1, _env_int("PANEL_HERMES_COOLDOWN_SECONDS", 60)),
        exclude_tools=exclude,
        scrubber_mode=mode,
        scrubber_url=_env("SCRUBBER_URL") or None,
        scrubber_jwt_secret=_env("SCRUBBER_JWT_SECRET") or None,
        novelty_window=max(1, _env_int("PANEL_HERMES_NOVELTY_WINDOW", 100)),
        queue_size=max(1, _env_int("PANEL_HERMES_QUEUE_SIZE", 200)),
    )
