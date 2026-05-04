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


def test_past_date_due_with_injected_clock():
    assert is_due({"due_date": date(2098, 12, 31)}, FakeClock()) is True


def test_without_injected_clock_uses_real_today_safely():
    # This catches implementations that blindly call clock.today() when clock is None.
    assert is_due({"due_date": date(2000, 1, 1)}) is True
    assert is_due({"due_date": date(2999, 1, 1)}) is False
