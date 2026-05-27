from panel_hermes_plugin._config import resolve_config


def test_config_defaults(monkeypatch):
    monkeypatch.setenv("PANEL_BASE_URL", "https://x")
    monkeypatch.setenv("PANEL_SITE_KEY", "pk")
    monkeypatch.setenv("PANEL_SITE_SECRET", "sk")

    cfg = resolve_config()
    assert cfg.enabled is True
    assert cfg.sample_rate == 0.1
    assert cfg.failure_threshold == 5
    assert cfg.cooldown_seconds == 60


def test_config_inert_without_required_env(monkeypatch):
    monkeypatch.delenv("PANEL_BASE_URL", raising=False)
    monkeypatch.delenv("PANEL_SITE_KEY", raising=False)
    monkeypatch.delenv("PANEL_SITE_SECRET", raising=False)
    cfg = resolve_config()
    assert cfg.enabled is False
