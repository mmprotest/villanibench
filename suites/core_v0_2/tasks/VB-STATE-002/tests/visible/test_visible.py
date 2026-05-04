import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from api.serializer import serialize_subscription

def test_cancelled_subscription_serializes_as_cancelled():
    rec = {"cancelled": True, "paid_until": 200, "now": 100}
    assert serialize_subscription(rec)["status"] == "cancelled"
