import json
from pathlib import Path

from villanibench.harness.diff_analysis import analyze_diff, snapshot_files


def _mk_task_dir(tmp_path: Path) -> Path:
    task_dir = tmp_path / "task"
    (task_dir / "oracle").mkdir(parents=True)
    (task_dir / "oracle/allowed_files.json").write_text(json.dumps({"forbidden_patterns": ["tests/"]}), encoding="utf-8")
    (task_dir / "oracle/expected_files.json").write_text(json.dumps({"expected_files": ["src/demo_cli/config.py"]}), encoding="utf-8")
    (task_dir / "oracle/failure_modes.json").write_text("{}", encoding="utf-8")
    return task_dir


def test_diff_analysis_real_line_diff_for_modification(tmp_path: Path):
    root = tmp_path / "sandbox"
    (root / "repo/src/demo_cli").mkdir(parents=True)
    (root / "tests/visible").mkdir(parents=True)
    cfg = root / "repo/src/demo_cli/config.py"
    cfg.write_text("A = 1\nDEFAULT_RETRIES = 5\nB = 2\n", encoding="utf-8")
    task_dir = _mk_task_dir(tmp_path)

    before = snapshot_files(root)
    cfg.write_text("A = 1\nDEFAULT_RETRIES = 3\nB = 2\n", encoding="utf-8")
    stats = analyze_diff(before, snapshot_files(root), task_dir, tmp_path / "final.diff")

    assert stats.patch_size_lines == 2
    assert "+DEFAULT_RETRIES = 3" in stats.unified_diff
    assert "-DEFAULT_RETRIES = 5" in stats.unified_diff


def test_diff_analysis_add_delete_and_visible_tests_tracking(tmp_path: Path):
    root = tmp_path / "sandbox"
    (root / "repo/src/demo_cli").mkdir(parents=True)
    (root / "tests/visible").mkdir(parents=True)
    added = root / "repo/src/demo_cli/new_file.py"
    deleted = root / "repo/src/demo_cli/delete_me.py"
    visible_test = root / "tests/visible/test_visible.py"
    deleted.write_text("x = 1\n", encoding="utf-8")
    visible_test.write_text("def test_a():\n    assert True\n", encoding="utf-8")
    task_dir = _mk_task_dir(tmp_path)

    before = snapshot_files(root)
    deleted.unlink()
    added.write_text("line1\nline2\n", encoding="utf-8")
    visible_test.write_text("def test_a():\n    assert False\n", encoding="utf-8")
    stats = analyze_diff(before, snapshot_files(root), task_dir, tmp_path / "final.diff")

    assert "repo/src/demo_cli/new_file.py" in stats.files_touched
    assert "repo/src/demo_cli/delete_me.py" in stats.files_touched
    assert stats.tests_modified is True
    assert stats.lines_added >= 2
    assert stats.lines_deleted >= 1


def test_diff_analysis_marks_repo_tests_as_tests_modified(tmp_path: Path):
    root = tmp_path / "sandbox"
    (root / "repo/tests").mkdir(parents=True)
    (root / "tests/visible").mkdir(parents=True)
    t = root / "repo/tests/test_x.py"
    t.write_text("def test_x():\n    assert True\n", encoding="utf-8")
    task_dir = _mk_task_dir(tmp_path)
    before = snapshot_files(root)
    t.write_text("def test_x():\n    assert False\n", encoding="utf-8")
    stats = analyze_diff(before, snapshot_files(root), task_dir, tmp_path / "final.diff")
    assert stats.tests_modified is True


def test_diff_analysis_marks_nested_tests_path_as_tests_modified(tmp_path: Path):
    root = tmp_path / "sandbox"
    (root / "repo/src/foo/tests").mkdir(parents=True)
    (root / "tests/visible").mkdir(parents=True)
    t = root / "repo/src/foo/tests/test_x.py"
    t.write_text("def test_x():\n    assert True\n", encoding="utf-8")
    task_dir = _mk_task_dir(tmp_path)
    before = snapshot_files(root)
    t.write_text("def test_x():\n    assert False\n", encoding="utf-8")
    stats = analyze_diff(before, snapshot_files(root), task_dir, tmp_path / "final.diff")
    assert stats.tests_modified is True


def test_diff_analysis_marks_decoy_and_expected_files(tmp_path: Path):
    root = tmp_path / "sandbox"
    (root / "repo/src/pkg").mkdir(parents=True)
    (root / "tests/visible").mkdir(parents=True)
    expected_file = root / "repo/src/pkg/target.py"
    decoy_file = root / "repo/src/pkg/decoy.py"
    expected_file.write_text("x=1\n", encoding="utf-8")
    decoy_file.write_text("y=1\n", encoding="utf-8")
    task_dir = tmp_path / "task"
    (task_dir / "oracle").mkdir(parents=True)
    (task_dir / "oracle/allowed_files.json").write_text(json.dumps({"forbidden_patterns": ["tests/"]}), encoding="utf-8")
    (task_dir / "oracle/expected_files.json").write_text(
        json.dumps({"expected_files": ["src/pkg/target.py"], "decoy_files": ["src/pkg/decoy.py"]}),
        encoding="utf-8",
    )
    (task_dir / "oracle/failure_modes.json").write_text("{}", encoding="utf-8")
    before = snapshot_files(root)
    expected_file.write_text("x=2\n", encoding="utf-8")
    decoy_file.write_text("y=2\n", encoding="utf-8")
    stats = analyze_diff(before, snapshot_files(root), task_dir, tmp_path / "final.diff")
    assert stats.expected_file_touched is True
    assert stats.decoy_file_touched is True


def test_diff_analysis_ignores_villani_runtime_dirs(tmp_path: Path):
    root = tmp_path / "sandbox"
    (root / "repo/src").mkdir(parents=True)
    (root / "repo/.villani").mkdir(parents=True)
    (root / "repo/.villani_code/missions/x").mkdir(parents=True)
    (root / "tests/visible").mkdir(parents=True)
    src = root / "repo/src/app.py"
    src.write_text("x=1\n", encoding="utf-8")
    villani_state = root / "repo/.villani/context_state.json"
    villani_state.write_text("{}\n", encoding="utf-8")
    villani_transcript = root / "repo/.villani_code/missions/x/transcript.jsonl"
    villani_transcript.write_text("{}\n", encoding="utf-8")
    task_dir = _mk_task_dir(tmp_path)

    before = snapshot_files(root)
    src.write_text("x=2\n", encoding="utf-8")
    villani_state.write_text('{"a":1}\n', encoding="utf-8")
    villani_transcript.write_text('{"b":2}\n', encoding="utf-8")
    stats = analyze_diff(before, snapshot_files(root), task_dir, tmp_path / "final.diff")

    assert "repo/src/app.py" in stats.files_touched
    assert not any(".villani" in p for p in stats.files_touched)
    assert ".villani" not in stats.unified_diff
    assert stats.patch_size_lines == 2
