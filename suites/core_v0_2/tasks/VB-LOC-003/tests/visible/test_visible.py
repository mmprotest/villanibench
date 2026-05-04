import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from reports.daily import group_daily_counts

def test_positive_timezone_moves_late_utc_event_to_next_day():
    assert group_daily_counts([{"timestamp_hour": 23}], account_offset_hours=10) == {"day-1": 1}
