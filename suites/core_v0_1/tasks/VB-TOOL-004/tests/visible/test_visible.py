import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from exporters.service import export

def test_csv_exporter_is_registered():
    assert export([["a", "b"], ["c", "d"]], "csv") == "a,b
c,d"
