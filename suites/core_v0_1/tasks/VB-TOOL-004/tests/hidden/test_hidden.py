import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from exporters.registry import EXPORTERS

def test_registry_contains_json_and_csv():
    assert set(EXPORTERS) == {"json", "csv"}
