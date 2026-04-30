import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from currency.api import convert_cents


def test_visible_case():
    assert convert_cents(105, 1.075) == 113
