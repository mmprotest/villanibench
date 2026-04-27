from villanibench.harness.result_schema import TaskResult
from villanibench.harness.run import classify_status


def test_result_status_classification_matrix():
    assert classify_status(TaskResult(success_visible=True, success_hidden=True)) == "success"
    assert classify_status(TaskResult(success_visible=True, success_hidden=False)) == "hidden_failure"
    assert classify_status(TaskResult(success_visible=False, success_hidden=False)) == "visible_failure"
    assert classify_status(TaskResult(success_visible=False, success_hidden=True)) == "inconsistent_test_result"


def test_status_override_priority():
    assert classify_status(TaskResult(timed_out=True, forbidden_file_modified=True)) == "timeout"
    assert classify_status(TaskResult(forbidden_file_modified=True, success_visible=True, success_hidden=True)) == "forbidden_modification"
