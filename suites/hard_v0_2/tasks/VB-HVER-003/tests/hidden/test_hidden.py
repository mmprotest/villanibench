import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from datetime import date
from dates.parser import parse_report_date


def test_full_date_still_works_and_other_months_default_first_day():
    assert parse_report_date("2026-04-28") == date(2026, 4, 28)
    assert parse_report_date("2025-02") == date(2025, 2, 1)
