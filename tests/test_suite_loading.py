from pathlib import Path

from villanibench.tasks.loader import load_suite


def test_suite_loading():
    suite, tasks = load_suite(Path("suites/core_v0_1"))
    assert suite.id == "villanibench-core-v0.1"
    assert len(tasks) == 10
    assert [task.id for task in tasks] == [
        "VB-LOC-001",
        "VB-LOC-002",
        "VB-LOC-003",
        "VB-LOC-004",
        "VB-LOC-005",
        "VB-MIN-001",
        "VB-MIN-002",
        "VB-MIN-003",
        "VB-MIN-004",
        "VB-MIN-005",
    ]
