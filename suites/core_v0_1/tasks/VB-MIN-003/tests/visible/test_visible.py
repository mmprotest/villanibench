import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "repo" / "src"))

from demo_validation.messages import validate_project_name


def test_empty_project_name_message():
    assert validate_project_name("") == "Project name is required"
