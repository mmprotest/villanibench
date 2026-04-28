import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from app.startup import start

def test_start_accepts_legacy_db_url_key():
    assert start({"DB_URL": "postgres://local"})["database_url"] == "postgres://local"
