import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from currency.api import convert_cents


def test_hidden_case():
    assert convert_cents(999, 0.815) == 814
