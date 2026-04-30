import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from retention.settings import DEFAULT_RETENTION_DAYS


def test_source_constant():
    assert DEFAULT_RETENTION_DAYS == 365
