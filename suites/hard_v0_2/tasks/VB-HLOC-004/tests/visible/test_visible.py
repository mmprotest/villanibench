import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "repo" / "src"))

from quota.api import used_units


def test_archived_resources_are_not_counted():
    resources = [
        {"name": "active-small", "units": 4, "archived": False},
        {"name": "archived-large", "units": 9, "archived": True},
    ]

    assert used_units(resources) == 4
