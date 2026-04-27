import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from demo_cli.cli import build_help_text


def test_help_uses_correct_default():
    assert "default: 3" in build_help_text()
