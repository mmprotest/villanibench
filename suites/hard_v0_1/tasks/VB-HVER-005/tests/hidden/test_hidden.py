import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from migrate.config import migrate_config


def test_zero_retry_count_is_preserved_and_missing_uses_default():
    migrated = migrate_config({"retry_count": 0})
    assert migrated["retry_count"] == 0
    assert migrate_config({}) == {"send_email": True, "retry_count": 3}
