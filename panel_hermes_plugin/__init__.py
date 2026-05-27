from __future__ import annotations

import logging
from typing import Any

import httpx

from ._config import resolve_config
from ._hooks import HookRuntime
from ._ingest import IngestWorker
from ._sampler import TraceSampler

logger = logging.getLogger(__name__)

try:
    from panel_sdk import AsyncPanelClient
except Exception:
    AsyncPanelClient = None


def _runtime_or_none() -> HookRuntime | None:
    cfg = resolve_config()
    if not cfg.enabled:
        return None
    if AsyncPanelClient is None:
        return None

    def factory() -> Any:
        http_client = httpx.AsyncClient(headers={"X-Agent-Trace": "hermes"})
        kwargs = {
            "base_url": cfg.base_url,
            "site_key": cfg.site_key,
            "site_secret": cfg.site_secret,
            "client": http_client,
        }
        if cfg.scrubber_mode in {"self-sign", "proxy"}:
            kwargs["scrubber_secret"] = cfg.scrubber_jwt_secret
            kwargs["scrubber_url"] = cfg.scrubber_url
        return AsyncPanelClient(**kwargs)

    ingest = IngestWorker(config=cfg, client_factory=factory)
    ingest.start()
    return HookRuntime(
        config=cfg,
        sampler=TraceSampler(sample_rate=cfg.sample_rate, novelty_window=cfg.novelty_window),
        ingest=ingest,
    )


def register(ctx: Any) -> None:
    runtime = None
    try:
        runtime = _runtime_or_none()
    except Exception as exc:
        logger.warning("panel-hermes-plugin initialization failed (fail-open): %s", exc)
        runtime = None

    if runtime is None:
        return

    def _wrap(name: str):
        fn = getattr(runtime, name)

        def _handler(**kwargs: Any) -> None:
            try:
                fn(**kwargs)
            except Exception as exc:
                logger.warning("panel-hermes-plugin hook %s failed (fail-open): %s", name, exc)

        return _handler

    ctx.register_hook("pre_api_request", _wrap("pre_api_request"))
    ctx.register_hook("post_api_request", _wrap("post_api_request"))
    ctx.register_hook("pre_llm_call", _wrap("pre_llm_call"))
    ctx.register_hook("post_llm_call", _wrap("post_llm_call"))
    ctx.register_hook("pre_tool_call", _wrap("pre_tool_call"))
    ctx.register_hook("post_tool_call", _wrap("post_tool_call"))
