import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from scheduler.api import runnable_jobs


def test_visible_case():
    data = [{"units": 4, "archived": False}, {"units": 9, "archived": True}] if 'runnable_jobs' == "used_units" else [{"name":"a", "enabled": True, "cron":"*"}, {"name":"b", "enabled": False, "cron":"*"}]
    result = runnable_jobs(data)
    assert result == (4 if 'runnable_jobs' == "used_units" else [{"name":"a", "enabled": True, "cron":"*"}])
