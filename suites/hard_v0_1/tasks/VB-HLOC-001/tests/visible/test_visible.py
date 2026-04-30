import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from checkout.api import compute_total


def test_visible_case():
    assert compute_total(100, 10, 20, 0.1) == 98.0
