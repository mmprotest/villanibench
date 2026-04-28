import sys
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from timecheck.window import is_due

class FakeClock:
    def today(self):
        return date(2099, 1, 1)

def test_future_date_not_due_with_injected_clock():
    assert is_due({"due_date": date(2099, 1, 2)}, FakeClock()) is False
