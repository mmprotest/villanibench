import csv
from io import StringIO

REQUIRED = ("id", "name", "amount")


def import_rows(text: str):
    reader = csv.DictReader(StringIO(text))
    rows = []
    for raw in reader:
        try:
            row = {key: raw[key].strip() for key in REQUIRED}
        except (KeyError, AttributeError):
            continue
        if any(not row[key] for key in REQUIRED):
            continue
        try:
            amount = int(row["amount"])
        except ValueError:
            continue
        rows.append({"id": row["id"], "name": row["name"], "amount": amount})
    return rows
