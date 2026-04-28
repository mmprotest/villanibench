import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'repo' / 'src'))

from reports.daily import group_day

def test_positive_offset_rolls_to_next_day():
    assert group_day(23 * 60 * 60, 10) == 1
