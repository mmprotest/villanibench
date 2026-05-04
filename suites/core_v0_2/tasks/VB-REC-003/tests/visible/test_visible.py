import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from api.service import get_ticket

def test_api_preserves_database_status():
    assert get_ticket("T1")["status"] == "closed"
