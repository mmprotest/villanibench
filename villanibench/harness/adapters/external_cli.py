from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import Mapping

from villanibench.harness.os_sandbox_user import grant_leaf_read_execute_access, grant_parent_traverse_access, sandbox_env
from villanibench.harness.process import run_command_tree_argv

from .common import resolve_executable_for_sandbox
from .base import AdapterRunResult, RunnerAdapter, now_iso


class ExternalCliAdapter(RunnerAdapter):
    def __init__(self, name: str, default_template: str):
        self.name = name
        self.default_template = default_template

    def resolve_template(self, config: dict) -> str:
        return str(config.get("command_template") or self.default_template)

    def _comparison_mode_and_warnings(self, template: str, config: dict) -> tuple[str, list[str]]:
        warnings: list[str] = []
        model_used = "{model}" in template
        base_url_provided = bool(config.get("base_url"))
        base_url_used = "{base_url}" in template
        strict = model_used and (base_url_used or not base_url_provided)
        if base_url_provided and not base_url_used:
            warnings.append("base_url_not_used_by_template")
        return ("strict" if strict else "non_strict"), warnings

    def render_command(self, template: str, **kwargs: str) -> str:
        return template.format(**kwargs)

    def run(self, task, sandbox_dir: Path, budget, config: dict) -> AdapterRunResult:
        output_dir = Path(config["task_output_dir"])
        stdout_path = output_dir / "runner_stdout.txt"
        stderr_path = output_dir / "runner_stderr.txt"
        template = self.resolve_template(config)
        prompt_file = (sandbox_dir / "prompt.txt").resolve()
        prompt_text = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else ""
        cwd = (sandbox_dir / "repo").resolve()
        comparison_mode, warnings = self._comparison_mode_and_warnings(template, config)
        command = self.render_command(
            template,
            prompt_file=str(prompt_file),
            prompt_text=prompt_text,
            cwd=str(cwd),
            model=str(config.get("model", "")),
            base_url=str(config.get("base_url", "")),
            api_key=str(config.get("api_key", "")),
            output_dir=str(output_dir.resolve()),
            visible_test_command=str(task.visible_test_command),
        )
        env = sandbox_env(os.environ.copy(), Path(config["task_output_dir"]))
        diag_path = output_dir / "adapter_diagnostics.txt"
        argv: list[str] = []

        started = now_iso()
        timed_out = False
        runner_crashed = False
        exit_code = 0
        with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
            try:
                try:
                    argv = shlex.split(command, posix=(os.name != "nt"))
                except ValueError as exc:
                    raise RuntimeError(
                        "Unable to parse command template for sandboxed execution. "
                        "Provide an absolute executable path in command_template."
                    ) from exc
                if not argv:
                    raise RuntimeError("Command template produced an empty command.")
                argv[0] = resolve_executable_for_sandbox(argv[0], env)
                exe = Path(argv[0])
                path_entries = [p for p in env.get("PATH", "").split(os.pathsep) if p]
                env_diag = redact_env_for_diagnostics(env)
                diag_lines = [
                    f"runner={self.name}",
                    f"rendered_command={command}",
                    f"argv={argv}",
                    f"resolved_executable={argv[0]}",
                    f"resolved_executable_exists={exe.exists()}",
                    f"resolved_executable_is_file={exe.is_file()}",
                    f"resolved_executable_suffix={exe.suffix}",
                    f"cwd={cwd}",
                    f"cwd_exists={cwd.exists()}",
                    f"path_entries_count={len(path_entries)}",
                    f"path_entries_head={path_entries[:5]}",
                    f"sandbox_enabled={bool(config.get('sandbox_identity'))}",
                    f"sandbox_username={getattr(config.get('sandbox_identity'), 'username', None)}",
                    f"env_redacted={env_diag}",
                ]
                venv_lines = detect_venv_runner_diagnostics(exe)
                diag_lines.extend(venv_lines)
                print(f"[adapter:{self.name}] command rendered: {command}", flush=True)
                print(f"[adapter:{self.name}] argv parsed argc={len(argv)} executable={argv[0]}", flush=True)
                print(f"[adapter:{self.name}] executable resolved path={argv[0]} exists={exe.exists()} is_file={exe.is_file()}", flush=True)
                print(f"[adapter:{self.name}] cwd={cwd} exists={cwd.exists()}", flush=True)
                print(f"[adapter:{self.name}] sandbox identity username={getattr(config.get('sandbox_identity'), 'username', None)} enabled={bool(config.get('sandbox_identity'))}", flush=True)
                if venv_lines:
                    print(f"[adapter:{self.name}] {venv_lines[0]}", flush=True)
                identity = config.get("sandbox_identity")
                if identity is not None and hasattr(identity, "username"):
                    prepare_sandbox_runner_access(self.name, identity, exe, env)
                    smoke_sandbox_runner_access(self.name, identity, exe, cwd, env, budget.wall_time_sec)
                diag_path.write_text("\n".join(diag_lines) + "\n", encoding="utf-8")
                completed = run_command_tree_argv(
                    argv,
                    cwd,
                    budget.wall_time_sec,
                    env=env,
                    sandbox_identity=config.get("sandbox_identity"),
                )
                out.write(completed.stdout)
                err.write(completed.stderr)
                timed_out = completed.timed_out
                exit_code = completed.exit_code
                runner_crashed = completed.exit_code != 0 and not completed.timed_out
            except Exception as exc:
                try:
                    with diag_path.open("a", encoding="utf-8") as df:
                        df.write(f"launch_error={type(exc).__name__}: {exc}\n")
                except Exception:
                    pass
                err.write(f"Adapter execution error: {exc}\n")
                runner_crashed = True
                exit_code = 1
        cli_error_patterns = (
            "No such option",
            "unrecognized arguments",
            "Usage:",
            "Missing argument",
            "Got unexpected extra argument",
        )
        notes = None
        if runner_crashed and stderr_path.exists():
            stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
            for pattern in cli_error_patterns:
                if pattern in stderr_text:
                    notes = f"External runner command appears invalid: {pattern}"
                    break

        ended = now_iso()
        return AdapterRunResult(
            exit_code=exit_code,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            started_at=started,
            ended_at=ended,
            timed_out=timed_out,
            runner_crashed=runner_crashed,
            raw_command=command,
            comparison_mode=comparison_mode,
            control_kind=None,
            setting_warnings=warnings,
            notes=notes,
        )


def redact_env_for_diagnostics(env: Mapping[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in env.items():
        ku = k.upper()
        if any(x in ku for x in ("KEY", "TOKEN", "SECRET", "PASSWORD", "AUTH")):
            out[k] = "<redacted>"
            continue
        if ku in {"PATH", "PYTHONPATH", "VIRTUAL_ENV", "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA"}:
            out[k] = v
    return out


def detect_venv_runner_diagnostics(executable: Path) -> list[str]:
    parts = [p.lower() for p in executable.parts]
    if "scripts" not in parts or (".venv" not in parts and "venv" not in parts):
        return []
    scripts_idx = parts.index("scripts")
    venv_path = Path(*executable.parts[:scripts_idx])
    python_exe = venv_path / "Scripts" / "python.exe"
    site_packages = venv_path / "Lib" / "site-packages"
    pth_files = list(site_packages.glob("*.pth")) if site_packages.exists() else []
    return [
        f"venv detected path={venv_path} python_exists={python_exe.exists()} site_packages_exists={site_packages.exists()} entrypoint_exists={executable.exists()} pth_files={len(pth_files)} pth_names={[p.name for p in pth_files]}",
    ]


def _detect_venv_root(executable: Path) -> Path | None:
    parts = [p.lower() for p in executable.parts]
    if "scripts" not in parts or (".venv" not in parts and "venv" not in parts):
        return None
    return Path(*executable.parts[:parts.index("scripts")])


def parse_pth_paths(site_packages: Path) -> tuple[list[Path], list[str]]:
    out: list[Path] = []
    unresolved: list[str] = []
    for pth in site_packages.glob("*.pth"):
        for line in pth.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if s.startswith("import"):
                unresolved.append(f"{pth.name}: import hook not statically resolved")
                continue
            p = Path(s)
            candidate = (pth.parent / p).resolve() if not p.is_absolute() else p.resolve()
            if candidate.exists():
                out.append(candidate)
    return out, unresolved


def prepare_sandbox_runner_access(adapter_name: str, identity, executable: Path, env: Mapping[str, str]) -> None:
    print(f"[adapter:{adapter_name}] sandbox runner access prepare start username={identity.username}", flush=True)
    grants: list[tuple[Path, str]] = [(executable, "runner_executable"), (executable.parent, "runner_executable_parent")]
    venv_root = _detect_venv_root(executable)
    unresolved: list[str] = []
    if venv_root is not None:
        site_packages = venv_root / "Lib" / "site-packages"
        grants.extend([
            (venv_root, "venv_root"),
            (venv_root / "Scripts", "venv_scripts"),
            (venv_root / "Lib", "venv_lib"),
            (site_packages, "site_packages"),
        ])
        python_exe = venv_root / "Scripts" / "python.exe"
        if python_exe.exists():
            grants.append((python_exe, "venv_python"))
        if site_packages.exists():
            pth_paths, unresolved = parse_pth_paths(site_packages)
            for path in pth_paths:
                if venv_root not in path.parents and path != venv_root:
                    grants.append((path, "editable_source"))
    seen: set[Path] = set()
    failed = 0
    done = 0
    for path, reason in grants:
        rp = path.resolve()
        if rp in seen or not rp.exists():
            continue
        seen.add(rp)
        try:
            grant_parent_traverse_access(identity, rp)
            grant_leaf_read_execute_access(identity, rp)
            done += 1
            print(f"[adapter:{adapter_name}] sandbox runner access grant path={rp} mode=read_execute reason={reason}", flush=True)
        except Exception as exc:
            failed += 1
            raise RuntimeError(f"sandbox runner access grant failed path={rp} reason={reason}: {exc}") from exc
    for note in unresolved:
        print(f"[adapter:{adapter_name}] sandbox runner access unresolved_pth {note}", flush=True)
    print(f"[adapter:{adapter_name}] sandbox runner access prepare done grants={done} failed={failed}", flush=True)


def smoke_sandbox_runner_access(adapter_name: str, identity, executable: Path, cwd: Path, env: Mapping[str, str], timeout_sec: float) -> None:
    venv_root = _detect_venv_root(executable)
    if venv_root is None:
        return
    python_exe = venv_root / "Scripts" / "python.exe"
    if not python_exe.exists():
        return
    print(f"[adapter:{adapter_name}] sandbox runner smoke test start executable={python_exe}", flush=True)
    result = run_command_tree_argv([str(python_exe), "-c", "import sys; print(sys.executable)"], cwd, min(timeout_sec, 20.0), env=dict(env), sandbox_identity=identity)
    print(f"[adapter:{adapter_name}] sandbox runner smoke test done exit_code={result.exit_code} stdout={result.stdout.strip()}", flush=True)
    if result.exit_code != 0:
        raise RuntimeError(f"sandbox runner smoke test failed for {python_exe}: {result.stderr.strip()}")
