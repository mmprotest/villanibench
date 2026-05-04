import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from plugins.loader import load_plugin

def test_text_plugin_loads_after_rename():
    assert load_plugin("text")("hello") == "HELLO"
