import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from migrate.config import migrate_config


def test_missing_values_use_defaults():
    assert migrate_config({}) == {"send_email": True, "retry_count": 3}


def test_false_and_zero_are_preserved_together():
    assert migrate_config({"send_email": False, "retry_count": 0}) == {
        "send_email": False,
        "retry_count": 0,
    }


def test_non_default_truthy_values_are_preserved():
    assert migrate_config({"send_email": True, "retry_count": 5}) == {
        "send_email": True,
        "retry_count": 5,
    }
