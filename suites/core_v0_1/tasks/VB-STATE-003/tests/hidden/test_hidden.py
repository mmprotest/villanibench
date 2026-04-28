import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from reports.inventory import report_reserved

def test_report_uses_same_reservation_delta():
    events = [{"type": "reserve", "quantity": 4}, {"type": "cancel", "quantity": 4}]
    assert report_reserved(events) == 0
