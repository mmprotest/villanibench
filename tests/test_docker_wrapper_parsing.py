import os
import subprocess
from pathlib import Path


def _write_fake_docker(bin_dir: Path) -> Path:
    log = bin_dir / "docker.log"
    docker = bin_dir / "docker"
    log.write_text("", encoding="utf-8")
    docker.write_text(f'''#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "{log}"
if [[ "$1" == "image" && "$2" == "inspect" ]]; then exit 1; fi
if [[ "$1" == "run" && "$2" == "--help" ]]; then echo "host-gateway"; exit 0; fi
exit 0
''', encoding="utf-8")
    docker.chmod(0o755)
    return log


def _run_wrapper(*args: str) -> list[str]:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "villanibench-docker"
    fake_bin = repo_root / ".tmp-test-bin"
    fake_bin.mkdir(exist_ok=True)
    log = _write_fake_docker(fake_bin)
    env = os.environ.copy(); env["PATH"] = f"{fake_bin}:{env['PATH']}"
    subprocess.run([str(script), *args], check=True, cwd=repo_root, env=env)
    return [l.strip() for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_rebuild_run_uses_default_image_and_preserves_run():
    lines = _run_wrapper("-Rebuild", "run", "--suite", "suites/core_v0_2")
    assert any("build -t villanibench:local" in x for x in lines)
    assert all("run:latest" not in x for x in lines)
    assert " villanibench:local run --suite suites/core_v0_2" in [x for x in lines if x.startswith("run --rm")][-1]


def test_image_option_overrides_default_image():
    lines = _run_wrapper("-Image", "custom:tag", "run", "--suite", "suites/core_v0_2")
    assert any("build -t custom:tag" in x for x in lines)


def test_double_dash_forwards_arguments():
    assert " run --suite suites/core_v0_2" in [x for x in _run_wrapper("--", "run", "--suite", "suites/core_v0_2") if x.startswith("run --rm")][-1]


def test_enable_nested_docker_adds_socket_mount_and_env():
    line = [x for x in _run_wrapper("--enable-nested-docker", "run", "--suite", "suites/core_v0_2") if x.startswith("run --rm")][-1]
    assert "/var/run/docker.sock" in line
    assert "VILLANIBENCH_ENABLE_NESTED_DOCKER=1" in line
