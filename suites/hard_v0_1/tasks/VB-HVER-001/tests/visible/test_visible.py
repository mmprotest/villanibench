import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from ingest.csv_importer import import_rows


def test_skips_row_with_missing_amount_but_keeps_valid_rows():
    text = '''id,name,amount
1,Ada,10
2,Bob,
3,Cam,5
'''
    assert import_rows(text) == [
        {"id": "1", "name": "Ada", "amount": 10},
        {"id": "3", "name": "Cam", "amount": 5},
    ]
