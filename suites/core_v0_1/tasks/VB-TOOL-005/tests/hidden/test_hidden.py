import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from cli.command import run

def test_normal_run_still_writes():
    assert run(["prod"]) == "WRITE prod"
