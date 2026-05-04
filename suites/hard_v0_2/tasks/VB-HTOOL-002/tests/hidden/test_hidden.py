import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from vb_htool_002.registry import resolve
from vb_htool_002.api import run


def test_existing_plugin_still_works_and_resolver_returns_callable():
    assert run("json", "x") == "json:x"
    assert resolve('sms')("y") == 'sms' + ":y"
