import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from slugs.settings import DEFAULT_SEPARATOR


def test_source_constant():
    assert DEFAULT_SEPARATOR == "-"
