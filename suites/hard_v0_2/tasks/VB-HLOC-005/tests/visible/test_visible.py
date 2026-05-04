import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "repo" / "src"))

from scheduler.api import runnable_jobs


def test_disabled_job_with_cron_is_not_runnable():
    jobs = [
        {"name": "a", "enabled": True, "cron": "* * * * *"},
        {"name": "b", "enabled": False, "cron": "* * * * *"},
    ]

    assert runnable_jobs(jobs) == [jobs[0]]
