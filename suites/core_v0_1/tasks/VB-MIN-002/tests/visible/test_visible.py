import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "repo" / "src"))

from demo_config.settings import resolve_timeout


def test_env_overrides_default_when_no_explicit(monkeypatch):
    monkeypatch.setenv("APP_TIMEOUT", "45")
    assert resolve_timeout(None) == 45
