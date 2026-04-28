from pathlib import Path

from villanibench.tasks.loader import load_suite


def test_suite_loading():
    suite, tasks = load_suite(Path("suites/core_v0_1"))
    assert suite.id == "villanibench-core-v0.1"
    assert len(tasks) == 5
    assert [task.id for task in tasks] == [
        "VB-MIN-001",
        "VB-MIN-002",
        "VB-MIN-003",
        "VB-MIN-004",
        "VB-MIN-005",
    ]
