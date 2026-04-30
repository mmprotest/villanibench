import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from quota.api import used_units


def test_hidden_case():
    data = [{"units": 4, "archived": False}, {"units": 9, "archived": True}] if 'used_units' == "used_units" else [{"name":"a", "enabled": True, "cron":"*"}, {"name":"b", "enabled": False, "cron":"*"}]
    result = used_units(data)
    assert result == (4 if 'used_units' == "used_units" else [{"name":"a", "enabled": True, "cron":"*"}])
