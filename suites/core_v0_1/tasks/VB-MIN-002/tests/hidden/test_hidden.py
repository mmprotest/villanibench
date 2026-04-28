import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "repo" / "src"))

from demo_config.settings import resolve_timeout, resolve_timeout_from_config


def test_explicit_overrides_env(monkeypatch):
    monkeypatch.setenv("APP_TIMEOUT", "45")
    assert resolve_timeout(12) == 12


def test_helper_path_uses_env_when_config_timeout_missing(monkeypatch):
    monkeypatch.setenv("APP_TIMEOUT", "0")
    assert resolve_timeout_from_config({"timeout": None}) == 0
