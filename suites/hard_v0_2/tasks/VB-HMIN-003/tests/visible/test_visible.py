import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from pages.api import get_default


def test_default_value():
    assert get_default() == 50
