from pathlib import Path


def test_dockerfile_exists():
    assert Path("Dockerfile").exists()


def test_dockerignore_exists_and_has_required_patterns():
    text = Path('.dockerignore').read_text(encoding='utf-8')
    for pat in [".git", "artifacts/", ".villani/", ".villani_code/", "*.gguf", "*.safetensors", "*.bin"]:
        assert pat in text


def test_wrappers_exist():
    assert Path("scripts/villanibench-docker").exists()
    assert Path("scripts/villanibench-docker.ps1").exists()


def test_unix_wrapper_mounts_only_repo_root_and_forwards_args():
    text = Path("scripts/villanibench-docker").read_text(encoding="utf-8")
    assert '"$REPO_ROOT:/work"' in text
    assert 'exec docker "${DOCKER_ARGS[@]}" "$IMAGE" "$@"' in text
    assert '/var/run/docker.sock' not in text
    assert '$HOME' not in text


def test_powershell_wrapper_mounts_only_repo_root_and_forwards_args():
    text = Path("scripts/villanibench-docker.ps1").read_text(encoding="utf-8")
    assert ':/work' in text
    assert '$dockerArgs += $BenchArgs' in text
    assert '/var/run/docker.sock' not in text


def test_run_py_uses_argv_for_docker_execution():
    text = Path("villanibench/harness/run.py").read_text(encoding="utf-8")
    assert 'run_command_tree_argv(docker_argv' in text
    assert '" ".join(docker_argv)' not in text


def test_process_argv_helper_uses_shell_false():
    text = Path("villanibench/harness/process.py").read_text(encoding="utf-8")
    assert 'def run_command_tree_argv' in text
    assert 'shell=False' in text
