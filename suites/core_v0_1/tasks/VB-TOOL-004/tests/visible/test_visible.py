from src.exporters import export


def test_csv_exporter_is_registered():
    assert export([["a", "b"], ["c", "d"]], "csv") == "a,b\nc,d"
