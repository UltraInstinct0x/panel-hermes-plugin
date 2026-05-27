# panel-hermes-plugin

Hermes plugin that forwards sampled conversation traces and tool-call units to panel ingest using `panel-sdk`.

## Install

```bash
pip install panel-hermes-plugin
```

Enable plugin in Hermes and ensure `plugin.yaml` is discoverable in the plugin folder.

## Required env

- `PANEL_BASE_URL`
- `PANEL_SITE_KEY`
- `PANEL_SITE_SECRET`

If missing, plugin is inert and fail-open.

## Optional env

- `PANEL_HERMES_POOL` (default `hermes-traces`)
- `PANEL_HERMES_SAMPLE_RATE` (default `0.1`)
- `PANEL_HERMES_DRY_RUN` (`true|false`, default `false`)
- `PANEL_HERMES_FAILURE_THRESHOLD` (default `5`)
- `PANEL_HERMES_COOLDOWN_SECONDS` (default `60`)
- `PANEL_HERMES_EXCLUDE_TOOLS` (default `read_file,search_files,browser_snapshot`)
- `PANEL_HERMES_SCRUBBER_MODE` (`off|self-sign|proxy`, default `off`)
- `SCRUBBER_URL`
- `SCRUBBER_JWT_SECRET`

## Behavior

- Sampling baseline (default 10%), plus always-on error and novelty sampling
- Async queue + background ingest worker
- Circuit breaker on repeated failures
- Dry run mode (no POST)
- Per-tool exclusion for noisy units
- Tool calls become `process_tool_call_rating` units
- Conversation history shipped as trace via `ingest_trace`

## Validation

```bash
pytest
ruff check .
ruff format --check .
```

## Development note

If `panel-sdk>=0.2.0` is unavailable from your package index, install from a local
checkout before running tests.
