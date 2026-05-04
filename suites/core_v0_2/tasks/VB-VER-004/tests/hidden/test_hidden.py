import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from datetime import date
import pytest
from dates.parser import parse_report_date


def test_dash_format_still_supported():
    assert parse_report_date("2026-04-28") == date(2026, 4, 28)


def test_validation_is_not_weakened_for_other_separators():
    for value in ["2026.04.28", "2026 04 28", "2026_04_28"]:
        with pytest.raises(ValueError):
            parse_report_date(value)


def test_mixed_dash_and_slash_formats_are_rejected():
    for value in ["2026/04-28", "2026-04/28"]:
        with pytest.raises(ValueError):
            parse_report_date(value)
