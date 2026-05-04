import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "repo" / "src"))

from quota.api import used_units


def test_counts_multiple_active_resources_and_excludes_multiple_archived_resources():
    resources = [
        {"name": "active-a", "units": 3, "archived": False},
        {"name": "archived-a", "units": 100, "archived": True},
        {"name": "active-b", "units": 8, "archived": False},
        {"name": "archived-b", "units": 200, "archived": True},
    ]

    assert used_units(resources) == 11


def test_missing_archived_field_is_treated_as_active_for_legacy_records():
    resources = [
        {"name": "legacy-active", "units": 6},
        {"name": "explicit-active", "units": 5, "archived": False},
        {"name": "archived", "units": 50, "archived": True},
    ]

    assert used_units(resources) == 11


def test_all_archived_resources_report_zero_usage():
    resources = [
        {"name": "old-a", "units": 7, "archived": True},
        {"name": "old-b", "units": 13, "archived": True},
    ]

    assert used_units(resources) == 0


def test_result_depends_on_input_values_not_visible_fixture_constants():
    resources = [
        {"name": "one", "units": 2, "archived": False},
        {"name": "two", "units": 5, "archived": False},
        {"name": "three", "units": 17, "archived": True},
    ]

    assert used_units(resources) == 7
