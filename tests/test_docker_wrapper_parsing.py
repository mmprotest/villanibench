import os
import subprocess
from pathlib import Path


def _write_fake_docker(bin_dir: Path) -> Path:
    log = bin_dir / "docker.log"
    docker = bin_dir / "docker"
    log.write_text("", encoding="utf-8")
    docker.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "{log}"
if [[ "$1" == "image" && "$2" == "inspect" ]]; then
  exit 1
fi
if [[ "$1" == "run" && "$2" == "--help" ]]; then
  echo "host-gateway"
  exit 0
fi
exit 0
""".format(log=log),
        encoding="utf-8",
    )
    docker.chmod(0o755)
    return log


def _run_wrapper(*args: str) -> list[str]:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "villanibench-docker"
    fake_bin = repo_root / ".tmp-test-bin"
    fake_bin.mkdir(exist_ok=True)
    log = _write_fake_docker(fake_bin)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    subprocess.run([str(script), *args], check=True, cwd=repo_root, env=env)
    return [line.strip() for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_rebuild_run_uses_default_image_and_preserves_run():
    lines = _run_wrapper("-Rebuild", "run", "--suite", "suites/core_v0_2")
    assert any("build -t villanibench:local" in line for line in lines)
    assert any("run:latest" in line for line in lines) is False
    final_run = [line for line in lines if line.startswith("run --rm")][-1]
    assert " villanibench:local run --suite suites/core_v0_2" in final_run


def test_image_option_overrides_default_image():
    lines = _run_wrapper("-Image", "custom:tag", "run", "--suite", "suites/core_v0_2")
    assert any("build -t custom:tag" in line for line in lines)
    final_run = [line for line in lines if line.startswith("run --rm")][-1]
    assert " custom:tag run --suite suites/core_v0_2" in final_run


def test_double_dash_forwards_arguments():
    lines = _run_wrapper("--", "run", "--suite", "suites/core_v0_2")
    final_run = [line for line in lines if line.startswith("run --rm")][-1]
    assert " villanibench:local run --suite suites/core_v0_2" in final_run


def test_validate_suite_forwards_positional_args():
    lines = _run_wrapper("validate-suite", "suites/core_v0_2")
    final_run = [line for line in lines if line.startswith("run --rm")][-1]
    assert " villanibench:local validate-suite suites/core_v0_2" in final_run
