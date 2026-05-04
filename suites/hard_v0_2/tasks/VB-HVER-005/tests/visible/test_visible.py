import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from migrate.config import migrate_config


def test_explicit_false_is_preserved():
    assert migrate_config({"send_email": False})["send_email"] is False


def test_explicit_zero_retry_count_is_preserved():
    assert migrate_config({"retry_count": 0})["retry_count"] == 0
