import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from ui.sidebar import show_project

def test_ui_uses_same_nested_permission_resolver():
    assert show_project([{"allow": True}, {"allow": False}]) is False
