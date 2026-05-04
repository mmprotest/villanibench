import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from retry_delay.settings import DEFAULT_RETRY_DELAY_MS


def test_source_constant():
    assert DEFAULT_RETRY_DELAY_MS == 30000
