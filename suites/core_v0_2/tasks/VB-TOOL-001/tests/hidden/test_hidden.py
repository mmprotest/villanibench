import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from app.startup import start

def test_new_database_url_still_wins():
    assert start({"DB_URL": "old", "DATABASE_URL": "new"})["database_url"] == "new"
