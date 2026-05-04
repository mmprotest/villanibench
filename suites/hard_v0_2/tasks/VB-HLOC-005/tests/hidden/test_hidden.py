import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "repo" / "src"))

from scheduler.api import runnable_jobs


def test_only_enabled_jobs_with_non_empty_cron_are_runnable():
    runnable_morning = {"name": "morning", "enabled": True, "cron": "0 9 * * *", "priority": 1}
    runnable_nightly = {"name": "nightly", "enabled": True, "cron": "0 0 * * *", "priority": 2}
    jobs = [
        {"name": "disabled_with_cron", "enabled": False, "cron": "* * * * *"},
        runnable_morning,
        {"name": "enabled_without_cron", "enabled": True},
        {"name": "enabled_empty_cron", "enabled": True, "cron": ""},
        {"name": "missing_enabled", "cron": "*/5 * * * *"},
        runnable_nightly,
    ]

    assert runnable_jobs(jobs) == [runnable_morning, runnable_nightly]
