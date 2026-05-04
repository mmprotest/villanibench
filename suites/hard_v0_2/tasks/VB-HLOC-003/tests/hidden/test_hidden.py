import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from currency.api import convert_cents


def test_hidden_fractional_rate_rounds_after_conversion():
    assert convert_cents(999, 0.815) == 814


def test_hidden_larger_amount_uses_same_source_of_truth():
    assert convert_cents(12345, 1.234) == 15234


def test_hidden_small_amount_returns_rounded_integer_cents():
    assert convert_cents(1, 0.6) == 1
