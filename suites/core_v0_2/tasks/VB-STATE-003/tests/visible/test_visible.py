import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from checkout.reservations import reserved_total

def test_cancel_releases_reserved_inventory():
    events = [{"type": "reserve", "quantity": 5}, {"type": "cancel", "quantity": 2}]
    assert reserved_total(events) == 3
