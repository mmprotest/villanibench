from __future__ import annotations

import json
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from villanibench.harness.adapters import build_adapter
from villanibench.harness.budget import get_budget_profile
from villanibench.harness.diff_analysis import analyze_diff, snapshot_files
from villanibench.harness.notes import append_note
from villanibench.harness.result_schema import TaskResult
from villanibench.harness.sandbox import copy_hidden_tests_to_sandbox_for_evaluation, prepare_sandbox
from villanibench.tasks.loader import load_suite


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    wall_time_sec: float = 0.0


def resolve_test_command_timeout_sec(budget_wall_time_sec: float, remaining_wall_time_sec: float | None = None) -> float:
    timeout_sec = min(60.0, max(5.0, float(budget_wall_time_sec) / 4.0))
    if remaining_wall_time_sec is not None:
        timeout_sec = min(timeout_sec, max(5.0, float(remaining_wall_time_sec)))
    return timeout_sec


def run_cmd(command: str, cwd: Path, timeout_sec: float) -> CommandResult:
    started = time.monotonic()
    try:
        proc = subprocess.run(command, cwd=cwd, shell=True, text=True, capture_output=True, timeout=timeout_sec)
        elapsed = time.monotonic() - started
        return CommandResult(
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            timed_out=False,
            wall_time_sec=elapsed,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - started
        stdout = exc.stdout if isinstance(exc.stdout, str) else ((exc.stdout or b"").decode(errors="replace"))
        stderr = exc.stderr if isinstance(exc.stderr, str) else ((exc.stderr or b"").decode(errors="replace"))
        timeout_message = f"Command timed out after {timeout_sec:.1f}s"
        stderr = f"{stderr.rstrip()}\n{timeout_message}".strip()
        return CommandResult(
            exit_code=124,
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
            wall_time_sec=elapsed,
        )


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
    log_progress = bool(config.get("log_progress"))

    def _log(message: str) -> None:
        if log_progress:
            print(message, flush=True)

    _log(
        f"[run] start run_id={run_id} suite={suite.id} runner={adapter.name} model={model} task_count={len(tasks)} output_dir={output_dir}"
    )

    for task_index, task in enumerate(tasks, start=1):
        _log(f"[task {task_index}/{len(tasks)}] start task_id={task.id}")
        task_output = output_dir / "tasks" / task.id
        task_output.mkdir(parents=True, exist_ok=True)
        resolved_budget_profile_id = task.budget_profile or suite.budget_profile
        if not resolved_budget_profile_id:
            raise RuntimeError(f"No budget profile configured for task {task.id} or suite {suite.id}")
        budget = get_budget_profile(resolved_budget_profile_id)
        result = TaskResult(
            run_id=run_id,
            suite_id=suite.id,
            task_id=task.id,
            runner=adapter.name,
            model=model,
            budget_profile=resolved_budget_profile_id,
            category=task.category,
        )
        try:
            sandbox, _repo = prepare_sandbox(task, task_output)
            test_timeout_sec = resolve_test_command_timeout_sec(budget.wall_time_sec)
            pre_visible = run_cmd(task.visible_test_command, sandbox, timeout_sec=test_timeout_sec)
            _log(
                f"[task {task_index}/{len(tasks)}] preflight visible exit_code={pre_visible.exit_code} timed_out={pre_visible.timed_out} elapsed={pre_visible.wall_time_sec:.2f}s"
            )
            result.preflight_visible_timed_out = pre_visible.timed_out
            if pre_visible.timed_out:
                result.status = "invalid_task"
                result.notes = append_note(result.notes, "Preflight visible test command timed out.")
                result.notes = append_note(result.notes, pre_visible.stderr.strip()[:500])
                (task_output / "result.json").write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
                results.append(result)
                continue
            if pre_visible.exit_code == 0:
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
            _log(f"[task {task_index}/{len(tasks)}] runner start budget_profile={resolved_budget_profile_id}")
            run_res = adapter.run(task, sandbox, budget, adapter_cfg)
            elapsed = time.monotonic() - start
            _log(
                f"[task {task_index}/{len(tasks)}] runner done elapsed={elapsed:.2f}s crashed={run_res.runner_crashed} timed_out={run_res.timed_out} budget_exceeded={run_res.budget_exceeded}"
            )
            result.wall_time_sec = round(elapsed, 4)
            result.comparison_mode = run_res.comparison_mode
            result.setting_warnings = run_res.setting_warnings
            result.runner_crashed = run_res.runner_crashed
            result.timed_out = run_res.timed_out
            result.budget_exceeded = run_res.budget_exceeded
            result.control_kind = run_res.control_kind
            if run_res.notes:
                result.notes = append_note(result.notes, run_res.notes)
            if run_res.trace_path:
                result.notes = append_note(result.notes, f"control_trace={run_res.trace_path.name}")

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

            post_visible = run_cmd(task.visible_test_command, sandbox, timeout_sec=test_timeout_sec)
            _log(
                f"[task {task_index}/{len(tasks)}] post visible exit_code={post_visible.exit_code} timed_out={post_visible.timed_out} elapsed={post_visible.wall_time_sec:.2f}s"
            )
            result.post_visible_timed_out = post_visible.timed_out
            result.success_visible = post_visible.exit_code == 0 and not post_visible.timed_out
            if post_visible.timed_out:
                result.notes = append_note(result.notes, "Post-run visible test command timed out.")
                result.notes = append_note(result.notes, post_visible.stderr.strip()[:500])
            if not result.timed_out:
                if (sandbox / "tests" / "hidden").exists():
                    result.forbidden_file_modified = True
                    note = "Runner created tests/hidden before evaluator copied hidden tests."
                    result.notes = append_note(result.notes, note)
                    raise RuntimeError(note)
                copy_hidden_tests_to_sandbox_for_evaluation(task, sandbox)
                post_hidden = run_cmd(task.hidden_test_command, sandbox, timeout_sec=test_timeout_sec)
                _log(
                    f"[task {task_index}/{len(tasks)}] post hidden exit_code={post_hidden.exit_code} timed_out={post_hidden.timed_out} elapsed={post_hidden.wall_time_sec:.2f}s"
                )
                result.hidden_timed_out = post_hidden.timed_out
                result.success_hidden = post_hidden.exit_code == 0 and not post_hidden.timed_out
                if post_hidden.timed_out:
                    result.notes = append_note(result.notes, "Hidden test command timed out.")
                    result.notes = append_note(result.notes, post_hidden.stderr.strip()[:500])

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
            if pre_visible.stderr:
                result.notes = append_note(result.notes, pre_visible.stderr.strip()[:500])
            if result.runner_crashed and result.status == "success":
                note = "Runner exited non-zero but final state passed visible and hidden tests."
                result.notes = append_note(result.notes, note)
        except Exception as exc:
            message = str(exc)
            if "Runner created tests/hidden before evaluator copied hidden tests." in message:
                result.status = "forbidden_modification"
            else:
                result.status = "harness_error"
            result.notes = append_note(result.notes, message)
            _log(f"[task {task_index}/{len(tasks)}] error status={result.status} message={message}")
        (task_output / "result.json").write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        results.append(result)
        _log(f"[task {task_index}/{len(tasks)}] done status={result.status}")

    jsonl_path = output_dir / "results.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r.to_dict()) + "\n")

    summary = {
        "run_id": run_id,
        "suite_id": suite.id,
        "runner": adapter.name,
        "model": model,
        "budget_profiles": sorted({r.budget_profile for r in results if r.budget_profile}),
        "task_count": len(results),
        "statuses": {
            s: sum(1 for r in results if r.status == s)
            for s in {r.status for r in results}
        },
    }
    (output_dir / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _log(f"[run] done run_id={run_id} statuses={summary['statuses']}")
    return summary
