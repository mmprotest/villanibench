import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from datetime import date
from dates.parser import parse_report_date

def test_dash_format_still_supported_and_invalid_rejected():
    assert parse_report_date("2026-04-28") == date(2026, 4, 28)
    try:
        parse_report_date("2026.04.28")
    except ValueError:
        pass
    else:
        raise AssertionError("dot format should remain invalid")
