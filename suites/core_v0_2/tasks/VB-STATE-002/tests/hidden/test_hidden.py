import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from workers.renewal import should_renew

def test_cancelled_subscription_is_not_renewed():
    rec = {"cancelled": True, "paid_until": 200, "now": 100}
    assert should_renew(rec) is False
