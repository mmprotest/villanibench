import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "repo" / "src"))

from demo_config.settings import DEFAULT_TIMEOUT, resolve_timeout


def test_env_timeout_used_when_no_explicit(monkeypatch):
    monkeypatch.setenv("APP_TIMEOUT", "45")
    assert resolve_timeout(None) == 45


def test_explicit_overrides_env(monkeypatch):
    monkeypatch.setenv("APP_TIMEOUT", "45")
    assert resolve_timeout(12) == 12


def test_default_used_when_no_explicit_or_env(monkeypatch):
    monkeypatch.delenv("APP_TIMEOUT", raising=False)
    assert resolve_timeout(None) == DEFAULT_TIMEOUT
