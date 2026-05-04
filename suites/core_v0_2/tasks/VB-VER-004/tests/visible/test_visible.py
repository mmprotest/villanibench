import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from datetime import date
from dates.parser import parse_report_date

def test_slash_format_is_supported():
    assert parse_report_date("2026/04/28") == date(2026, 4, 28)
