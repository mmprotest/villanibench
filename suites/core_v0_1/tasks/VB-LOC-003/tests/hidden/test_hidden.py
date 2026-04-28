import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'repo' / 'src'))

from reports.daily import group_day

def test_negative_offset_rolls_to_previous_day():
    assert group_day(2 * 60 * 60, -5) == -1
