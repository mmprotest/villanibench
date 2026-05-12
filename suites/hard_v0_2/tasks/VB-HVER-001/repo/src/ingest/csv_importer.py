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
            break
        if any(not row[key] for key in REQUIRED):
            break
        try:
            amount = int(row["amount"])
        except ValueError:
            break
        rows.append({"id": row["id"], "name": row["name"], "amount": amount})
    return rows
