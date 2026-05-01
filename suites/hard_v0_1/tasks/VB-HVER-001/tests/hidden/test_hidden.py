import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from ingest.csv_importer import import_rows


def test_skips_non_numeric_amount_and_blank_name():
    text = '''id,name,amount
1,Ada,7
2,,4
3,Cam,nope
4,Dee,9
'''
    assert import_rows(text) == [
        {"id": "1", "name": "Ada", "amount": 7},
        {"id": "4", "name": "Dee", "amount": 9},
    ]
