import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from boolenv.settings import TRUE_VALUES


def test_source_constant():
    assert TRUE_VALUES == {"1", "true", "yes", "on"}
