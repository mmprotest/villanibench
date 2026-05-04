import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from demo_cli.config import DEFAULT_RETRIES


def test_source_of_truth_value_is_three():
    assert DEFAULT_RETRIES == 3
