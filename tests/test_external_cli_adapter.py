import subprocess

from pathlib import Path

from villanibench.harness.adapters.external_cli import ExternalCliAdapter
from villanibench.harness.adapters.external_cli import (
    _detect_venv_root,
    detect_venv_runner_diagnostics,
    parse_pth_paths,
    prepare_sandbox_runner_access,
    redact_env_for_diagnostics,
)
from villanibench.harness.budget import get_budget_profile


class T:
    visible_test_command = "pytest tests/visible"


def test_external_cli_runs_fake_command_and_substitutes(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    (sandbox / "repo/src/demo_cli").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("hello", encoding="utf-8")
    cfg = sandbox / "repo/src/demo_cli/config.py"
    cfg.write_text("DEFAULT_RETRIES = 5\n", encoding="utf-8")
    adapter = ExternalCliAdapter(
        "fake",
        "python -c \"from pathlib import Path; p=Path('src/demo_cli/config.py'); p.write_text(p.read_text().replace('DEFAULT_RETRIES = 5', 'DEFAULT_RETRIES = 3'))\"",
    )
    out = tmp_path / "out"
    out.mkdir()
    res = adapter.run(T(), sandbox, get_budget_profile("lite_v0_1"), {
        "task_output_dir": str(out), "model": "m", "base_url": "u", "api_key": "k"
    })
    assert res.exit_code == 0
    assert "DEFAULT_RETRIES = 3" in cfg.read_text(encoding="utf-8")


def test_missing_cli_is_runner_crash(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    (sandbox / "repo").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("x", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    adapter = ExternalCliAdapter("fake", "definitely_missing_command_zz")
    res = adapter.run(T(), sandbox, get_budget_profile("lite_v0_1"), {"task_output_dir": str(out), "model": "m"})
    assert res.runner_crashed is True


def test_timeout_reported(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    (sandbox / "repo").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("x", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    adapter = ExternalCliAdapter("fake", "python -c \"import time; time.sleep(2)\"")
    b = get_budget_profile("lite_v0_1")
    object.__setattr__(b, "wall_time_sec", 1)
    res = adapter.run(T(), sandbox, b, {"task_output_dir": str(out), "model": "m"})
    assert res.timed_out is True


def test_external_cli_sets_utf8_env(tmp_path: Path, monkeypatch):
    sandbox = tmp_path / "sandbox"
    (sandbox / "repo").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("x", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    seen = {}

    def _fake_run_command_tree(argv, cwd, timeout_sec, env=None, stdin_text=None, sandbox_identity=None):
        seen["env"] = env or {}
        class R:
            exit_code = 0
            stdout = ""
            stderr = ""
            timed_out = False
        return R()

    monkeypatch.setattr("villanibench.harness.adapters.external_cli.run_command_tree_argv", _fake_run_command_tree)
    adapter = ExternalCliAdapter("fake", "echo hi")
    res = adapter.run(T(), sandbox, get_budget_profile("lite_v0_1"), {"task_output_dir": str(out), "model": "m"})
    assert res.exit_code == 0
    assert seen["env"].get("PYTHONIOENCODING") == "utf-8"
    assert seen["env"].get("PYTHONUTF8") == "1"


def test_external_cli_usage_error_adds_note(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    (sandbox / "repo").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("x", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    adapter = ExternalCliAdapter("fake", 'python -c "import sys; print(\'No such option: --prompt-file\', file=sys.stderr); sys.exit(2)"')
    res = adapter.run(T(), sandbox, get_budget_profile("lite_v0_1"), {"task_output_dir": str(out), "model": "m"})
    assert res.runner_crashed is True
    assert res.notes is not None
    assert "External runner command appears invalid" in res.notes


def test_external_cli_resolves_executable_before_sandbox_launch(tmp_path: Path, monkeypatch):
    sandbox = tmp_path / "sandbox"
    (sandbox / "repo").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("x", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    seen = {}

    monkeypatch.setattr(
        "villanibench.harness.adapters.external_cli.resolve_executable_for_sandbox",
        lambda cmd, env=None: "/usr/local/bin/villani-code",
    )

    def _fake_run(argv, cwd, timeout_sec, env=None, stdin_text=None, sandbox_identity=None):
        seen["argv"] = argv
        seen["sandbox_identity"] = sandbox_identity
        class R:
            exit_code = 0
            stdout = ""
            stderr = ""
            timed_out = False
        return R()

    monkeypatch.setattr("villanibench.harness.adapters.external_cli.run_command_tree_argv", _fake_run)
    adapter = ExternalCliAdapter("villani", 'villani-code run --repo "{cwd}" "{prompt_text}"')
    res = adapter.run(T(), sandbox, get_budget_profile("lite_v0_1"), {
        "task_output_dir": str(out), "model": "m", "sandbox_identity": object()
    })
    assert res.exit_code == 0
    assert seen["argv"][0] == "/usr/local/bin/villani-code"
    assert seen["sandbox_identity"] is not None


def test_redact_env_for_diagnostics():
    out = redact_env_for_diagnostics({
        "PATH": "/a:/b",
        "API_KEY": "secret",
        "AUTH_TOKEN": "tok",
        "TMP": "/tmp",
    })
    assert out["API_KEY"] == "<redacted>"
    assert out["AUTH_TOKEN"] == "<redacted>"
    assert out["PATH"] == "/a:/b"


def test_detect_venv_runner_diagnostics(tmp_path: Path):
    exe = tmp_path / ".venv" / "Scripts" / "villani-code.exe"
    py = tmp_path / ".venv" / "Scripts" / "python.exe"
    sp = tmp_path / ".venv" / "Lib" / "site-packages"
    exe.parent.mkdir(parents=True)
    sp.mkdir(parents=True)
    exe.write_text("", encoding="utf-8")
    py.write_text("", encoding="utf-8")
    (sp / "editable.pth").write_text("x", encoding="utf-8")
    lines = detect_venv_runner_diagnostics(exe)
    assert lines
    assert "python_exists=True" in lines[0]
    assert "pth_files=1" in lines[0]


def test_detect_venv_root_from_scripts_path(tmp_path: Path):
    exe = tmp_path / ".venv" / "Scripts" / "tool.exe"
    assert _detect_venv_root(exe) == (tmp_path / ".venv")


def test_parse_pth_paths_absolute_and_ignore_import(tmp_path: Path):
    sp = tmp_path / ".venv" / "Lib" / "site-packages"
    sp.mkdir(parents=True)
    src = tmp_path / "srcpkg"
    src.mkdir()
    (sp / "a.pth").write_text(f"# hi\n{src}\nimport x\n\n", encoding="utf-8")
    paths, unresolved = parse_pth_paths(sp)
    assert src in paths
    assert unresolved and "import hook" in unresolved[0]


def test_prepare_sandbox_runner_access_plans_read_execute(monkeypatch, tmp_path: Path):
    exe = tmp_path / ".venv" / "Scripts" / "tool.exe"
    sp = tmp_path / ".venv" / "Lib" / "site-packages"
    src = tmp_path / "editable_src"
    exe.parent.mkdir(parents=True)
    sp.mkdir(parents=True)
    src.mkdir()
    exe.write_text("", encoding="utf-8")
    (tmp_path / ".venv" / "Scripts" / "python.exe").write_text("", encoding="utf-8")
    (sp / "ed.pth").write_text(str(src), encoding="utf-8")
    calls = []
    monkeypatch.setattr("villanibench.harness.adapters.external_cli.grant_parent_traverse_access", lambda ident, path: calls.append(("parent", path)))
    monkeypatch.setattr("villanibench.harness.adapters.external_cli.grant_leaf_read_execute_access", lambda ident, path: calls.append(("leaf", path)))
    prepare_sandbox_runner_access("villani", type("I", (), {"username": "u"})(), exe, {})
    assert any(kind == "leaf" and p == sp for kind, p in calls)
    assert any(kind == "leaf" and p == src for kind, p in calls)


from villanibench.harness.adapters.external_cli import _is_under_windows_user_profile, _runner_env_root, prepare_runner_env_for_sandbox, RunnerEnvPlan


def test_profile_executable_detection_windows(monkeypatch):
    assert _is_under_windows_user_profile(Path(r"C:\Users\Simon\x\tool.exe"))


def test_runner_env_path_under_programdata(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ProgramData", str(tmp_path / "ProgramData"))
    root = _runner_env_root(Path(r"C:\Users\Simon\a\.venv\Scripts\tool.exe"), Path(r"C:\Users\Simon\a\.venv"))
    assert "runner_envs" in str(root)


def test_prepare_runner_env_rewrites_executable_and_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ProgramData", str(tmp_path / "ProgramData"))
    src = tmp_path / "Users" / "Simon" / "repo" / ".venv"
    exe = src / "Scripts" / "villani-code.exe"
    (src / "Scripts").mkdir(parents=True)
    (src / "Lib" / "site-packages").mkdir(parents=True)
    exe.write_text("", encoding="utf-8")
    (src / "Scripts" / "python.exe").write_text("", encoding="utf-8")
    env = {"PATH": str(src / "Scripts")}
    monkeypatch.setattr("villanibench.harness.adapters.external_cli.prepare_sandbox_runner_access", lambda *a, **k: None)
    plan = prepare_runner_env_for_sandbox("villani", type("I", (), {"username": "u"})(), exe, env)
    assert isinstance(plan, RunnerEnvPlan)
    assert "ProgramData" in str(plan.executable)
    assert plan.env["VIRTUAL_ENV"].endswith(".venv")


def test_unparseable_import_hook_fails(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ProgramData", str(tmp_path / "ProgramData"))
    src = tmp_path / "Users" / "Simon" / "repo" / ".venv"
    exe = src / "Scripts" / "villani-code.exe"
    sp = src / "Lib" / "site-packages"
    sp.mkdir(parents=True)
    (src / "Scripts").mkdir(parents=True)
    exe.write_text("", encoding="utf-8")
    (src / "Scripts" / "python.exe").write_text("", encoding="utf-8")
    (sp / "bad.pth").write_text("import something", encoding="utf-8")
    monkeypatch.setattr("villanibench.harness.adapters.external_cli.prepare_sandbox_runner_access", lambda *a, **k: None)
    try:
        prepare_runner_env_for_sandbox("villani", type("I", (), {"username": "u"})(), exe, {"PATH": str(src / "Scripts")})
        assert False
    except RuntimeError as exc:
        assert "Unparseable editable import-hook" in str(exc)
