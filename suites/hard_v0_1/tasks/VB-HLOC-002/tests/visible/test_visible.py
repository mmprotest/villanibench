import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from sla.api import breached


def test_visible_case():
    assert breached(70, 20, 60) == False
