import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from vb_htool_001.registry import resolve
from vb_htool_001.api import run


def test_existing_json_plugin_still_works():
    assert run("json", "x") == "json:x"
    assert resolve("json")("y") == "json:y"


def test_yaml_plugin_is_registered_through_api_and_resolver():
    assert run("yaml", "x") == "yaml:x"
    assert resolve("yaml")("y") == "yaml:y"


def test_unknown_exporter_still_raises_keyerror():
    with pytest.raises(KeyError):
        resolve("toml")
