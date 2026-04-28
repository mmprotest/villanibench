import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from importer.csv_import import import_users

def test_multiple_malformed_rows_are_skipped_only():
    rows = ["bad", "Linus,linus@example.com", ",missing@example.com", "Ken,ken@example.com"]
    assert import_users(rows) == [
        {"name": "Linus", "email": "linus@example.com"},
        {"name": "Ken", "email": "ken@example.com"},
    ]
