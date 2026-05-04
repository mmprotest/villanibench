import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from importer.csv_import import import_users

def test_valid_rows_after_malformed_row_are_kept():
    rows = ["Ada,ada@example.com", "bad row", "Grace,grace@example.com"]
    assert import_users(rows) == [
        {"name": "Ada", "email": "ada@example.com"},
        {"name": "Grace", "email": "grace@example.com"},
    ]
