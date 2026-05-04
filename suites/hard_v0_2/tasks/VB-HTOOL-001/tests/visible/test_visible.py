import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from vb_htool_001.api import run


def test_missing_plugin_is_registered():
    assert run('yaml', "x") == 'yaml' + ":x"
