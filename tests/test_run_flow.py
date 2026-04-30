import json
from pathlib import Path

from villanibench.harness.adapters.external_cli import ExternalCliAdapter
from villanibench.harness.adapters.base import AdapterRunResult, RunnerAdapter, now_iso
from villanibench.harness.run import run_cmd, run_suite





def _single_task_suite(tmp_path: Path) -> Path:
    suite_dir = tmp_path / "suite"
    task_src = Path("suites/core_v0_1/tasks/VB-MIN-001")
    task_dst = suite_dir / "tasks" / "VB-MIN-001"
    import shutil
    shutil.copytree(task_src, task_dst)
    (suite_dir / "suite.yaml").write_text(
        "\n".join([
            "id: core-fixture", "name: core fixture", "version: 0.1", "description: fixture",
            "task_count: 1", "categories:", "  - minimal_patch", "budget_profile: lite_v0_1", "visibility: mixed",
        ]) + "\n", encoding="utf-8"
    )
    return suite_dir

def test_hidden_tests_are_isolated_until_post_runner(tmp_path: Path, monkeypatch):
    adapter = ExternalCliAdapter(
        "fake_external",
        "python -c \"from pathlib import Path; import sys; sys.exit(1 if Path('../tests/hidden').exists() or Path('tests/hidden').exists() else 0)\"",
    )
    monkeypatch.setattr("villanibench.harness.run.build_adapter", lambda _name: adapter)

    out = tmp_path / "run"
    run_suite(_single_task_suite(tmp_path), "fake_external", "dummy", out, {})

    task_dir = out / "tasks" / "VB-MIN-001"
    result = json.loads((task_dir / "result.json").read_text(encoding="utf-8"))
    assert result["runner_crashed"] is False
    assert (task_dir / "sandbox/tests/hidden").exists()


def test_external_fake_runner_end_to_end_fixes_task(tmp_path: Path, monkeypatch):
    adapter = ExternalCliAdapter(
        "fake_external",
        "python -c \"from pathlib import Path; p=Path('src/demo_cli/config.py'); p.write_text(p.read_text().replace('DEFAULT_RETRIES = 5', 'DEFAULT_RETRIES = 3'))\"",
    )
    monkeypatch.setattr("villanibench.harness.run.build_adapter", lambda _name: adapter)

    out = tmp_path / "run"
    run_suite(_single_task_suite(tmp_path), "fake_external", "dummy", out, {})

    task_dir = out / "tasks" / "VB-MIN-001"
    result = json.loads((task_dir / "result.json").read_text(encoding="utf-8"))
    diff_text = (task_dir / "final.diff").read_text(encoding="utf-8")

    assert result["status"] == "success"
    assert result["success_visible"] is True
    assert result["success_hidden"] is True
    assert result["expected_file_touched"] is True
    assert result["tests_modified"] is False
    assert result["forbidden_file_modified"] is False
    assert result["patch_size_lines"] <= 4
    assert "DEFAULT_RETRIES = 5" in diff_text
    assert "DEFAULT_RETRIES = 3" in diff_text
    assert "tests/hidden" not in diff_text


def test_runner_created_hidden_tests_is_forbidden_modification(tmp_path: Path, monkeypatch):
    adapter = ExternalCliAdapter(
        "fake_external",
        "python -c \"from pathlib import Path; Path('../tests/hidden').mkdir(parents=True, exist_ok=True); Path('../tests/hidden/evil.py').write_text('x=1')\"",
    )
    monkeypatch.setattr("villanibench.harness.run.build_adapter", lambda _name: adapter)

    out = tmp_path / "run"
    run_suite(_single_task_suite(tmp_path), "fake_external", "dummy", out, {})
    result = json.loads((out / "tasks" / "VB-MIN-001/result.json").read_text(encoding='utf-8'))
    assert result["status"] == "forbidden_modification"
    assert "Runner created tests/hidden before evaluator copied hidden tests." in result["notes"]


def test_run_cmd_times_out():
    result = run_cmd('python -c "import time; time.sleep(10)"', Path("."), timeout_sec=0.2)
    assert result.timed_out is True
    assert result.exit_code != 0
    assert "Command timed out after" in result.stderr


def test_run_cmd_quick_success():
    result = run_cmd('python -c "print(123)"', Path("."), timeout_sec=2)
    assert result.timed_out is False
    assert result.exit_code == 0
    assert result.stdout.strip() == "123"


def test_hanging_visible_test_command_does_not_hang_harness(tmp_path: Path, monkeypatch):
    suite_dir = tmp_path / "suite"
    task_dir = suite_dir / "tasks" / "T-001"
    (task_dir / "repo/src/demo").mkdir(parents=True)
    (task_dir / "tests/visible").mkdir(parents=True)
    (task_dir / "tests/hidden").mkdir(parents=True)
    (task_dir / "oracle").mkdir(parents=True)
    (task_dir / "repo/src/demo/app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (task_dir / "prompt.txt").write_text("fix", encoding="utf-8")
    (task_dir / "tests/visible/test_visible.py").write_text("def test_visible():\n    assert False\n", encoding="utf-8")
    (task_dir / "tests/hidden/test_hidden.py").write_text("def test_hidden():\n    assert True\n", encoding="utf-8")
    (task_dir / "oracle/expected_files.json").write_text("[]", encoding="utf-8")
    (task_dir / "oracle/allowed_files.json").write_text("[]", encoding="utf-8")
    (task_dir / "oracle/failure_modes.json").write_text("[]", encoding="utf-8")
    (task_dir / "task.yaml").write_text(
        "\n".join(
            [
                "id: T-001",
                "title: t",
                "category: minimal_patch",
                "difficulty: easy",
                "language: python",
                "framework: pytest",
                "prompt_file: prompt.txt",
                "repo_dir: repo",
                'visible_test_command: python -c "import time; time.sleep(100)"',
                'hidden_test_command: python -c "print(1)"',
                "budget_profile: lite_v0_1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (suite_dir / "suite.yaml").write_text(
        "\n".join(
            [
                "id: suite-x",
                "name: s",
                "version: 0.1",
                "description: d",
                "task_count: 1",
                "categories:",
                "  - minimal_patch",
                "budget_profile: lite_v0_1",
                "visibility: mixed",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    adapter = ExternalCliAdapter("fake_external", 'python -c "print(1)"')
    monkeypatch.setattr("villanibench.harness.run.build_adapter", lambda _name: adapter)
    out = tmp_path / "run"
    summary = run_suite(suite_dir, "fake_external", "dummy", out, {})
    result = json.loads((out / "tasks" / "T-001/result.json").read_text(encoding="utf-8"))
    assert summary["task_count"] == 1
    assert result["status"] == "invalid_task"
    assert result["preflight_visible_timed_out"] is True


def test_result_uses_suite_budget_profile_when_task_budget_missing(tmp_path: Path, monkeypatch):
    suite_dir = tmp_path / "suite_budget"
    task_dir = suite_dir / "tasks" / "T-002"
    (task_dir / "repo/src/demo").mkdir(parents=True)
    (task_dir / "tests/visible").mkdir(parents=True)
    (task_dir / "tests/hidden").mkdir(parents=True)
    (task_dir / "oracle").mkdir(parents=True)
    (task_dir / "repo/src/demo/app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (task_dir / "prompt.txt").write_text("fix", encoding="utf-8")
    (task_dir / "tests/visible/test_visible.py").write_text("def test_visible():\n    assert True\n", encoding="utf-8")
    (task_dir / "tests/hidden/test_hidden.py").write_text("def test_hidden():\n    assert True\n", encoding="utf-8")
    (task_dir / "oracle/expected_files.json").write_text("[]", encoding="utf-8")
    (task_dir / "oracle/allowed_files.json").write_text("[]", encoding="utf-8")
    (task_dir / "oracle/failure_modes.json").write_text("[]", encoding="utf-8")
    (task_dir / "task.yaml").write_text(
        "\n".join(
            [
                "id: T-002",
                "title: t",
                "category: minimal_patch",
                "difficulty: easy",
                "language: python",
                "framework: pytest",
                "prompt_file: prompt.txt",
                "repo_dir: repo",
                'visible_test_command: python -c "import sys; sys.exit(1)"',
                'hidden_test_command: python -c "import sys; sys.exit(1)"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (suite_dir / "suite.yaml").write_text(
        "\n".join(
            [
                "id: suite-budget",
                "name: s",
                "version: 0.1",
                "description: d",
                "task_count: 1",
                "categories:",
                "  - minimal_patch",
                "budget_profile: lite_v0_1",
                "visibility: mixed",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    adapter = ExternalCliAdapter("fake_external", 'python -c "print(1)"')
    monkeypatch.setattr("villanibench.harness.run.build_adapter", lambda _name: adapter)
    out = tmp_path / "run_budget"
    run_suite(suite_dir, "fake_external", "dummy", out, {})
    result = json.loads((out / "tasks" / "T-002/result.json").read_text(encoding="utf-8"))
    assert result["budget_profile"] == "lite_v0_1"


def test_run_suite_calls_prepare_and_cleanup(tmp_path: Path, monkeypatch):
    class _Adapter(RunnerAdapter):
        name = "fake"
        def __init__(self): self.calls = []
        def prepare(self, task, sandbox_dir: Path, config: dict) -> None: self.calls.append("prepare")
        def cleanup(self, sandbox_dir: Path) -> None: self.calls.append("cleanup")
        def run(self, task, sandbox_dir: Path, budget, config: dict) -> AdapterRunResult:
            self.calls.append("run")
            return AdapterRunResult(0, sandbox_dir/"o.txt", sandbox_dir/"e.txt", now_iso(), now_iso(), False, False, "x", "strict", "external")

    adapter = _Adapter()
    monkeypatch.setattr("villanibench.harness.run.build_adapter", lambda _name: adapter)
    out = tmp_path / "run"
    run_suite(_single_task_suite(tmp_path), "fake", "dummy", out, {})
    assert adapter.calls == ["prepare", "run", "cleanup"]
