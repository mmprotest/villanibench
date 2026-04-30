import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from datetime import date
from dates.parser import parse_report_date


def test_month_only_defaults_to_first_day():
    assert parse_report_date("2026-04") == date(2026, 4, 1)
