from __future__ import annotations

import hashlib
import os
import shlex
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Mapping

from villanibench.harness.os_sandbox_user import grant_leaf_read_execute_access, grant_parent_traverse_access, sandbox_env
from villanibench.harness.process import run_command_tree_argv

from .common import resolve_executable_for_sandbox
from .base import AdapterRunResult, RunnerAdapter, now_iso


IGNORE_COPY_DIRS = {".git", ".venv", "artifacts", "runs", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "node_modules"}


@dataclass
class RunnerEnvPlan:
    executable: Path
    env: dict[str, str]


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
        command = self.render_command(template, prompt_file=str(prompt_file), prompt_text=prompt_text, cwd=str(cwd), model=str(config.get("model", "")), base_url=str(config.get("base_url", "")), api_key=str(config.get("api_key", "")), output_dir=str(output_dir.resolve()), visible_test_command=str(task.visible_test_command))
        env = sandbox_env(os.environ.copy(), Path(config["task_output_dir"]))
        diag_path = output_dir / "adapter_diagnostics.txt"
        argv: list[str] = []

        started = now_iso()
        timed_out = False
        runner_crashed = False
        exit_code = 0
        with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
            try:
                argv = shlex.split(command, posix=(os.name != "nt"))
                if not argv:
                    raise RuntimeError("Command template produced an empty command.")
                argv[0] = resolve_executable_for_sandbox(argv[0], env)
                exe = Path(argv[0])
                identity = config.get("sandbox_identity")
                if os.name == "nt" and identity is not None and hasattr(identity, "username"):
                    plan = prepare_runner_env_for_sandbox(self.name, identity, exe, env)
                    argv[0] = str(plan.executable)
                    env = plan.env
                    exe = plan.executable
                    smoke_sandbox_runner_access(self.name, identity, exe, cwd, env, budget.wall_time_sec)
                elif identity is not None and hasattr(identity, "username"):
                    prepare_sandbox_runner_access(self.name, identity, exe, env)
                    smoke_sandbox_runner_access(self.name, identity, exe, cwd, env, budget.wall_time_sec)
                diag_path.write_text(f"argv={argv}\nresolved_executable={argv[0]}\n", encoding="utf-8")
                completed = run_command_tree_argv(argv, cwd, budget.wall_time_sec, env=env, sandbox_identity=identity)
                out.write(completed.stdout)
                err.write(completed.stderr)
                timed_out = completed.timed_out
                exit_code = completed.exit_code
                runner_crashed = completed.exit_code != 0 and not completed.timed_out
            except Exception as exc:
                err.write(f"Adapter execution error: {exc}\n")
                runner_crashed = True
                exit_code = 1
        ended = now_iso()
        return AdapterRunResult(exit_code=exit_code, stdout_path=stdout_path, stderr_path=stderr_path, started_at=started, ended_at=ended, timed_out=timed_out, runner_crashed=runner_crashed, raw_command=command, comparison_mode=comparison_mode, control_kind=None, setting_warnings=warnings, notes=("External runner command appears invalid: No such option" if runner_crashed and exit_code!=0 and "No such option" in stderr_path.read_text(encoding="utf-8", errors="replace") else None))


def _is_under_windows_user_profile(path: Path) -> bool:
    raw = str(path).replace("/", "\\")
    parts = [p.lower() for p in PureWindowsPath(raw).parts]
    
    for i,part in enumerate(parts[:-1]):
        if part == "users" and i+1 < len(parts):
            return True
    return False


def _detect_venv_root(executable: Path) -> Path | None:
    parts = [p.lower() for p in executable.parts]
    if "scripts" not in parts or (".venv" not in parts and "venv" not in parts):
        return None
    return Path(*executable.parts[:parts.index("scripts")])


def _runner_env_root(executable: Path, venv_root: Path | None = None) -> Path:
    seed = f"{executable.resolve()}|{venv_root or ''}|{os.environ.get('PYTHON_VERSION','')}"
    stable = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    base = Path(os.environ.get("ProgramData", "C:/ProgramData")) / "villanibench" / "runner_envs"
    return base / stable


def _copytree_filtered(src: Path, dst: Path) -> None:
    def _ignore(_dir: str, names: list[str]):
        return [n for n in names if n in IGNORE_COPY_DIRS]
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=_ignore)


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


def prepare_runner_env_for_sandbox(adapter_name: str, identity, executable: Path, env: Mapping[str, str]) -> RunnerEnvPlan:
    if not _is_under_windows_user_profile(executable):
        prepare_sandbox_runner_access(adapter_name, identity, executable, env)
        return RunnerEnvPlan(executable=executable, env=dict(env))
    if os.environ.get("VILLANIBENCH_DISABLE_RUNNER_ENV_MIRROR") == "1":
        prepare_sandbox_runner_access(adapter_name, identity, executable, env)
        return RunnerEnvPlan(executable=executable, env=dict(env))
    print(f"[adapter:{adapter_name}] runner executable under user profile; preparing sandbox runner env path={executable}", flush=True)
    venv_root = _detect_venv_root(executable)
    if venv_root is None:
        raise RuntimeError("Profile-hosted runner executable is not in a venv Scripts path; unsupported for mirror")
    root = _runner_env_root(executable, venv_root)
    target_venv = root / ".venv"
    print(f"[adapter:{adapter_name}] runner env prepare start source_venv={venv_root} target_venv={target_venv}", flush=True)
    start = time.time()
    target_venv.mkdir(parents=True, exist_ok=True)
    for rel in ["Scripts", "Lib/site-packages"]:
        _copytree_filtered(venv_root / rel, target_venv / rel)
    if (venv_root / "pyvenv.cfg").exists():
        shutil.copy2(venv_root / "pyvenv.cfg", target_venv / "pyvenv.cfg")
    sp = target_venv / "Lib" / "site-packages"
    for pth in sp.glob("*.pth"):
        lines = pth.read_text(encoding="utf-8", errors="replace").splitlines()
        rewritten = []
        for ln in lines:
            s = ln.strip()
            if s.startswith("import"):
                raise RuntimeError(f"Unparseable editable import-hook in {pth.name}; install runner non-editably or extend parser")
            if s and not s.startswith("#"):
                src = (sp / s).resolve() if not Path(s).is_absolute() else Path(s).resolve()
                if _is_under_windows_user_profile(src):
                    tgt = root / "editable_sources" / src.name
                    _copytree_filtered(src, tgt)
                    rewritten.append(str(tgt))
                    print(f"[adapter:{adapter_name}] editable source copied source={src} target={tgt}", flush=True)
                    print(f"[adapter:{adapter_name}] pth rewritten file={pth} old={src} new={tgt}", flush=True)
                    continue
            rewritten.append(ln)
        pth.write_text("\n".join(rewritten) + "\n", encoding="utf-8")
    copied_exe = target_venv / "Scripts" / executable.name
    env2 = dict(env)
    env2["VIRTUAL_ENV"] = str(target_venv)
    path_entries = [p for p in env2.get("PATH", "").split(os.pathsep) if p]
    source_scripts = str(venv_root / "Scripts")
    path_entries = [str(target_venv / "Scripts")] + [p for p in path_entries if Path(p) != Path(source_scripts)]
    env2["PATH"] = os.pathsep.join(path_entries)
    pypath = env2.get("PYTHONPATH")
    if pypath:
        kept = [p for p in pypath.split(os.pathsep) if not _is_under_windows_user_profile(Path(p))]
        env2["PYTHONPATH"] = os.pathsep.join(kept)
    prepare_sandbox_runner_access(adapter_name, identity, root, env2)
    print(f"[adapter:{adapter_name}] runner env copy done files=unknown elapsed={time.time()-start:.2f}", flush=True)
    print(f"[adapter:{adapter_name}] executable rewritten old={executable} new={copied_exe}", flush=True)
    return RunnerEnvPlan(executable=copied_exe, env=env2)


def prepare_sandbox_runner_access(adapter_name: str, identity, executable: Path, env: Mapping[str, str]) -> None:
    grants = [executable, executable.parent]
    venv_root = _detect_venv_root(executable)
    if venv_root is not None:
        sp = venv_root / "Lib" / "site-packages"
        grants.extend([venv_root, venv_root/"Scripts", venv_root/"Lib", sp])
        pth_paths,_ = parse_pth_paths(sp) if sp.exists() else ([],[])
        grants.extend(pth_paths)
    seen=set()
    for g in grants:
        if g in seen or not g.exists():
            continue
        seen.add(g)
        grant_parent_traverse_access(identity, g)
        grant_leaf_read_execute_access(identity, g)


def smoke_sandbox_runner_access(adapter_name: str, identity, executable: Path, cwd: Path, env: Mapping[str, str], timeout_sec: float) -> None:
    venv_root = _detect_venv_root(executable)
    if venv_root is None:
        return
    python_exe = venv_root / "Scripts" / "python.exe"
    if not python_exe.exists():
        return
    print(f"[adapter:{adapter_name}] sandbox runner smoke test start executable={python_exe}", flush=True)
    result = run_command_tree_argv([str(python_exe), "-c", "import sys; print(sys.executable)"], cwd, min(timeout_sec, 20.0), env=dict(env), sandbox_identity=identity)
    print(f"[adapter:{adapter_name}] sandbox runner smoke test done exit_code={result.exit_code}", flush=True)


def detect_venv_runner_diagnostics(executable: Path) -> list[str]:
    parts = [p.lower() for p in executable.parts]
    if "scripts" not in parts or (".venv" not in parts and "venv" not in parts):
        return []
    scripts_idx = parts.index("scripts")
    venv_path = Path(*executable.parts[:scripts_idx])
    python_exe = venv_path / "Scripts" / "python.exe"
    site_packages = venv_path / "Lib" / "site-packages"
    pth_files = list(site_packages.glob("*.pth")) if site_packages.exists() else []
    return [f"venv detected path={venv_path} python_exists={python_exe.exists()} site_packages_exists={site_packages.exists()} entrypoint_exists={executable.exists()} pth_files={len(pth_files)} pth_names={[p.name for p in pth_files]}"]


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
