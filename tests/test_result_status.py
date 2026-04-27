from villanibench.harness.result_schema import TaskResult
from villanibench.harness.run import classify_status


def test_result_status_classification():
    r = TaskResult(success_visible=True, success_hidden=True)
    assert classify_status(r) == "success"
    r = TaskResult(timed_out=True)
    assert classify_status(r) == "timeout"
    r = TaskResult(runner_crashed=True)
    assert classify_status(r) == "runner_crash"
