import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from reports.daily import group_daily_counts

def test_negative_timezone_moves_early_utc_event_to_previous_day():
    assert group_daily_counts([{"timestamp_hour": 1}], account_offset_hours=-5) == {"day--1": 1}
