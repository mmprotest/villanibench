import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from pages.settings import DEFAULT_PAGE_SIZE


def test_source_constant():
    assert DEFAULT_PAGE_SIZE == 50
