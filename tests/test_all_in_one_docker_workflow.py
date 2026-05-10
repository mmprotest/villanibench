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
    assert 'dst=/work' in text
    assert 'exec docker "${DOCKER_ARGS[@]}" "$IMAGE" "$@"' in text
    assert '-EnableNestedDocker' in text
    assert '$HOME' not in text


def test_powershell_wrapper_mounts_only_repo_root_and_forwards_args():
    text = Path("scripts/villanibench-docker.ps1").read_text(encoding="utf-8")
    assert 'dst=/work' in text
    assert '$dockerArgs += $BenchArgs' in text
    assert '-EnableNestedDocker' in text


def test_run_py_uses_argv_for_docker_execution():
    text = Path("villanibench/harness/run.py").read_text(encoding="utf-8")
    assert 'run_command_tree_argv(docker_argv' in text
    assert '" ".join(docker_argv)' not in text


def test_process_argv_helper_uses_shell_false():
    text = Path("villanibench/harness/process.py").read_text(encoding="utf-8")
    assert 'def run_command_tree_argv' in text
    assert 'shell=False' in text


def test_powershell_wrapper_local_mode_build_args_and_staging_guardrails():
    text = Path("scripts/villanibench-docker.ps1").read_text(encoding="utf-8")
    assert 'VILLANI_CODE_INSTALL_MODE=$mode' in text
    assert 'VILLANI_CODE_SOURCE_IN_CONTEXT=/tmp/villani-code-src' in text
    assert 'Staged local source missing required manifest after copy.' in text


def test_powershell_wrapper_does_not_reset_staged_source_inside_build_block():
    text = Path("scripts/villanibench-docker.ps1").read_text(encoding="utf-8")
    build_block = text.split('if ($Rebuild -or -not $imageExists) {', 1)[1].split('}\nif (Test-Path $staged)', 1)[0]
    assert 'Remove-Item -Recurse -Force $staged' not in build_block
    assert 'New-Item -ItemType Directory -Force -Path $staged' not in build_block


def test_powershell_wrapper_robocopy_exit_code_handling():
    text = Path("scripts/villanibench-docker.ps1").read_text(encoding="utf-8")
    assert 'if ($LASTEXITCODE -ge 8)' in text
    assert 'robocopy failed with exit code $LASTEXITCODE' in text


def test_wrapper_mount_specs_use_docker_mount_key_value_pairs_without_rw():
    unix_text = Path("scripts/villanibench-docker").read_text(encoding="utf-8")
    ps_text = Path("scripts/villanibench-docker.ps1").read_text(encoding="utf-8")
    assert 'type=bind,src=$REPO_ROOT,dst=/work' in unix_text
    assert 'type=bind,src=$SANDBOX_ROOT,dst=/sandboxes' in unix_text
    assert 'type=bind,src=$repoRoot,dst=/work' in ps_text
    assert 'type=bind,src=$sandboxHostRoot,dst=/sandboxes' in ps_text
    assert 'dst=/work,rw' not in unix_text
    assert 'dst=/sandboxes,rw' not in unix_text
    assert 'dst=/work,rw' not in ps_text
    assert 'dst=/sandboxes,rw' not in ps_text


def test_nested_agent_docker_mount_specs_do_not_include_rw():
    text = Path("villanibench/harness/docker.py").read_text(encoding="utf-8")
    assert 'dst=/workspace,rw' not in text
    assert 'dst=/artifacts,rw' not in text
    assert 'dst=/workspace' in text
    assert 'dst=/artifacts' in text
