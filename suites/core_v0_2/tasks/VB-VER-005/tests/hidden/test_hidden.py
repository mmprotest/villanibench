import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from config.migrate import migrate_config


def test_old_timeout_key_migrates_and_default_does_not_override():
    assert migrate_config({"timeout": 12})["timeout_seconds"] == 12
    assert migrate_config({"timeout_seconds": 9})["timeout_seconds"] == 9


def test_missing_timeout_default_applies_to_any_new_config_shape():
    assert migrate_config({})["timeout_seconds"] == 30
    assert migrate_config({"features": ["beta"]})["timeout_seconds"] == 30
