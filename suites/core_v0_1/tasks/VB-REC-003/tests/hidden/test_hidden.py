import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from api.serializer import serialize_ticket

def test_serializer_preserves_other_status_values():
    assert serialize_ticket({"id": "T2", "status": "pending", "title": "Wait"})["status"] == "pending"
