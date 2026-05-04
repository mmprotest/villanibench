import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from plugins.registry import REGISTRY

def test_registry_points_at_existing_text_plugin_module():
    assert REGISTRY["text"] == "plugins.text_plugin:render"
