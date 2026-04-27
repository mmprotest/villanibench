from pathlib import Path

from villanibench.tasks.loader import load_suite


def test_suite_loading():
    suite, tasks = load_suite(Path("suites/core_v0_1"))
    assert suite.id == "villanibench-core-v0.1"
    assert len(tasks) == 1
    assert tasks[0].id == "VB-MIN-001"
