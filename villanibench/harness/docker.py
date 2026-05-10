from __future__ import annotations

import os
import shutil
from pathlib import Path


def ensure_docker_available() -> None:
    if not shutil.which("docker"):
        raise RuntimeError("Docker mode enabled, but `docker` CLI is not available on PATH.")


def build_docker_argv(
    *,
    image: str,
    host_workspace_dir: Path,
    command_argv: list[str],
    network: str = "none",
    read_only_rootfs: bool = True,
    env: dict[str, str] | None = None,
) -> list[str]:
    host = str(host_workspace_dir.resolve())
    argv: list[str] = [
        "docker",
        "run",
        "--rm",
        "--network",
        network,
    ]
    if read_only_rootfs:
        argv.append("--read-only")
    argv.extend(
        [
            "--mount",
            f"type=bind,src={host},dst=/workspace",
            "--mount",
            "type=tmpfs,dst=/tmp",
            "--mount",
            "type=tmpfs,dst=/var/tmp",
            "-w",
            "/workspace",
        ]
    )
    for k, v in (env or {}).items():
        argv.extend(["-e", f"{k}={v}"])
    argv.append(image)
    argv.extend(command_argv)
    return argv


def docker_env_from_config(config: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in ("api_key", "base_url", "model"):
        value = config.get(key)
        if value:
            out[key.upper()] = str(value)
    return out


def build_nested_agent_docker_argv(*, image: str, host_workspace_dir: Path, host_artifact_dir: Path, command_argv: list[str], env: dict[str, str] | None = None, network: str = "bridge") -> list[str]:
    argv = ["docker", "run", "--rm", "--read-only", "--network", network,
            "--mount", f"type=bind,src={host_workspace_dir.resolve()},dst=/workspace",
            "--mount", f"type=bind,src={host_artifact_dir.resolve()},dst=/artifacts",
            "--mount", "type=tmpfs,dst=/tmp", "--mount", "type=tmpfs,dst=/var/tmp", "-w", "/workspace"]
    for k, v in (env or {}).items():
        argv.extend(["-e", f"{k}={v}"])
    argv.append(image)
    argv.extend(command_argv)
    return argv
