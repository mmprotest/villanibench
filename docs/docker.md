# Docker workflow

VillaniBench supports an all-in-one Docker workflow: Docker on the host, benchmark execution inside container.

## Build image

```bash
./scripts/villanibench-docker --rebuild validate-suite suites/core_v0_1
```

## Run benchmark

```bash
./scripts/villanibench-docker run \
  --suite suites/core_v0_1 \
  --runner minimal_react_control \
  --model qwen3.6-9b \
  --base-url http://host.docker.internal:1234 \
  --api-key dummy \
  --output-dir artifacts/runs/control_qwen9b
```

## Compare runs

```bash
./scripts/villanibench-docker compare \
  --runs artifacts/runs/control_qwen9b artifacts/runs/villani_qwen9b \
  --output-dir artifacts/comparisons/qwen9b
```

## Windows PowerShell

```powershell
./scripts/villanibench-docker.ps1 run `
  --suite suites/core_v0_1 `
  --runner minimal_react_control `
  --model qwen3.6-9b `
  --base-url http://host.docker.internal:1234 `
  --api-key dummy `
  --output-dir artifacts/runs/control_qwen9b
```

## Host model servers

Use `host.docker.internal` to reach a model server running on the host from inside container. On Linux, wrapper scripts add `--add-host=host.docker.internal:host-gateway` when supported.

## Artifacts

Artifacts are written under the mounted repo (for example `artifacts/runs/...`) and persist on host.

## Notes and limitations

- Inner per-task sandbox isolation is still enforced; runners only receive sandbox repo paths.
- `--docker` on `villanibench run` is nested Docker mode. It is usually unnecessary with outer wrapper scripts.
- If nested Docker is requested inside the image without `/var/run/docker.sock`, VillaniBench prints a warning and nested mode will fail.
- The base image includes Python, pytest, git, and VillaniBench. External runner CLIs (Villani Code / Claude Code / OpenCode / Aider / Qwen CLI) must be present on PATH in the runtime image to use those adapters.
