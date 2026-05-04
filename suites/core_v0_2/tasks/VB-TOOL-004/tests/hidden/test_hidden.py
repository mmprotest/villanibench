import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from exporters.csv_exporter import export_csv
from exporters.json_exporter import export_json
from exporters.registry import EXPORTERS
from exporters.service import export


def test_registry_contains_existing_json_and_csv_exporters():
    assert set(EXPORTERS) == {"json", "csv"}
    assert EXPORTERS["json"] is export_json
    assert EXPORTERS["csv"] is export_csv


def test_csv_export_uses_existing_exporter_for_non_visible_rows():
    rows = [["name", "score", "active"], ["Ada", 10, True], ["Lin", 7, False]]
    assert export(rows, "csv") == "name,score,active\nAda,10,True\nLin,7,False"


def test_json_export_behavior_is_preserved():
    rows = [["x", 1], ["y", 2]]
    assert export(rows, "json") == str(rows)


def test_unknown_export_format_still_raises_key_error():
    try:
        export([["a"]], "xml")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown formats should not silently fall back to csv or json")
