import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from checkout.api import compute_total


def test_hidden_case():
    assert compute_total(200, 5, 50, 0.2) == 185.0
