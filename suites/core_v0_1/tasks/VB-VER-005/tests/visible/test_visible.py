import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from config.migrate import migrate_config

def test_missing_timeout_gets_documented_default():
    assert migrate_config({"name": "demo"})["timeout_seconds"] == 30
