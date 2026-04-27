from __future__ import annotations

import json
import subprocess
import time
import uuid
from pathlib import Path

from villanibench.harness.adapters import build_adapter
from villanibench.harness.budget import get_budget_profile
from villanibench.harness.diff_analysis import analyze_diff, snapshot_files
from villanibench.harness.result_schema import TaskResult
from villanibench.harness.sandbox import copy_hidden_tests_to_sandbox_for_evaluation, prepare_sandbox
from villanibench.tasks.loader import load_suite


def run_cmd(command: str, cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(command, cwd=cwd, shell=True, text=True, capture_output=True)
    return proc.returncode, proc.stdout, proc.stderr


def classify_status(result: TaskResult) -> str:
    if result.timed_out:
        return "timeout"
    if result.forbidden_file_modified:
        return "forbidden_modification"
    if result.budget_exceeded:
        return "budget_exceeded"
    if result.runner_crashed and not (result.success_visible and result.success_hidden):
        return "runner_crash"
    if result.success_visible and result.success_hidden:
        return "success"
    if result.success_visible and not result.success_hidden:
        return "hidden_failure"
    if not result.success_visible and result.success_hidden:
        return "inconsistent_test_result"
    if not result.success_visible and not result.success_hidden:
        return "visible_failure"
    return "harness_error"


def run_suite(suite_dir: Path, runner: str, model: str, output_dir: Path, config: dict) -> dict:
    suite, tasks = load_suite(suite_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())
    adapter = build_adapter(runner)
    results: list[TaskResult] = []

    for task in tasks:
        task_output = output_dir / "tasks" / task.id
        task_output.mkdir(parents=True, exist_ok=True)
        budget = get_budget_profile(task.budget_profile or suite.budget_profile)
        result = TaskResult(
            run_id=run_id,
            suite_id=suite.id,
            task_id=task.id,
            runner=adapter.name,
            model=model,
            budget_profile=task.budget_profile,
            category=task.category,
        )
        try:
            sandbox, _repo = prepare_sandbox(task, task_output)
            pre_visible_code, _, pre_visible_err = run_cmd(task.visible_test_command, sandbox)
            if pre_visible_code == 0:
                result.status = "invalid_task"
                result.notes = "Visible tests pass before runner"
                (task_output / "result.json").write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
                results.append(result)
                continue
            hidden_path = sandbox / "tests" / "hidden"
            if hidden_path.exists():
                raise RuntimeError("Hidden tests leaked into runner-visible sandbox before runner execution")

            before = snapshot_files(sandbox)
            start = time.monotonic()
            adapter_cfg = {
                **config,
                "model": model,
                "task_output_dir": str(task_output),
            }
            run_res = adapter.run(task, sandbox, budget, adapter_cfg)
            elapsed = time.monotonic() - start
            result.wall_time_sec = round(elapsed, 4)
            result.comparison_mode = run_res.comparison_mode
            result.setting_warnings = run_res.setting_warnings
            result.runner_crashed = run_res.runner_crashed
            result.timed_out = run_res.timed_out
            result.control_kind = run_res.control_kind

            after = snapshot_files(sandbox)
            diff_stats = analyze_diff(before, after, task.task_dir, task_output / "final.diff")
            result.files_touched = diff_stats.files_touched
            result.lines_added = diff_stats.lines_added
            result.lines_deleted = diff_stats.lines_deleted
            result.patch_size_lines = diff_stats.patch_size_lines
            result.tests_modified = diff_stats.tests_modified
            result.forbidden_file_modified = diff_stats.forbidden_file_modified
            result.expected_file_touched = diff_stats.expected_file_touched
            result.decoy_file_touched = diff_stats.decoy_file_touched

            post_visible_code, _, _ = run_cmd(task.visible_test_command, sandbox)
            result.success_visible = post_visible_code == 0
            if not result.timed_out:
                copy_hidden_tests_to_sandbox_for_evaluation(task, sandbox)
                post_hidden_code, _, _ = run_cmd(task.hidden_test_command, sandbox)
                result.success_hidden = post_hidden_code == 0

            telem = adapter.collect_telemetry(sandbox)
            result.model_calls = telem.model_calls
            result.tokens_input = telem.tokens_input
            result.tokens_output = telem.tokens_output
            result.shell_commands = telem.shell_commands
            result.file_reads = telem.file_reads
            result.file_writes = telem.file_writes
            result.telemetry_completeness = telem.telemetry_completeness
            result.missing_telemetry = telem.missing_telemetry

            result.status = classify_status(result)
            if pre_visible_err:
                result.notes = pre_visible_err.strip()[:500]
            if result.runner_crashed and result.status == "success":
                note = "Runner exited non-zero but final state passed visible and hidden tests."
                result.notes = f"{result.notes}\n{note}" if result.notes else note
        except Exception as exc:
            result.status = "harness_error"
            result.notes = str(exc)
        (task_output / "result.json").write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        results.append(result)

    jsonl_path = output_dir / "results.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r.to_dict()) + "\n")

    summary = {
        "run_id": run_id,
        "suite_id": suite.id,
        "runner": adapter.name,
        "model": model,
        "task_count": len(results),
        "statuses": {
            s: sum(1 for r in results if r.status == s)
            for s in {r.status for r in results}
        },
    }
    (output_dir / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
