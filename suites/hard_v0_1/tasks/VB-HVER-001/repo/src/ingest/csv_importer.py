import csv
from io import StringIO

REQUIRED = ("id", "name", "amount")


def import_rows(text: str):
    reader = csv.DictReader(StringIO(text))
    rows = []
    for raw in reader:
        # BUG: one malformed row aborts the whole import.
        row = {key: raw[key].strip() for key in REQUIRED}
        rows.append({"id": row["id"], "name": row["name"], "amount": int(row["amount"])})
    return rows
