import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "repo" / "src"))

from demo_validation.messages import validate_many


def test_batch_validation_uses_same_message():
    assert validate_many(["ok", " "])[1] == "Project name is required"
