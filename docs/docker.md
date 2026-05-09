# Docker workflow

- **Convenience mode**: harness and agent run in one container (reproducible, not hard isolation).
- **Nested isolation mode**: add `--enable-nested-docker` / `-EnableNestedDocker` to run each agent step in a fresh per-task container.

PowerShell convenience:
```powershell
.\scripts\villanibench-docker.ps1 -Rebuild run `
  --suite suites/core_v0_2 `
  --runner minimal_react_control `
  --model "qwen3.6-35b" `
  --base-url "http://host.docker.internal:1234" `
  --api-key dummy `
  --output-dir artifacts/runs/control
```

PowerShell nested isolation:
```powershell
.\scripts\villanibench-docker.ps1 -Rebuild -EnableNestedDocker run `
  --suite suites/core_v0_2 `
  --runner villani `
  --model "villanis/models/qwen3.6-35b-a3b-ud-iq4_xs.gguf" `
  --base-url "http://host.docker.internal:1234" `
  --api-key dummy `
  --output-dir artifacts/runs/villani_35b_core_v0_2_local
```

`host.docker.internal` reaches host LM Studio from containers. On Linux, wrappers add `--add-host host.docker.internal:host-gateway` when supported.

The Villani runner requires `villani-code` in the image PATH. Build with `--build-arg VILLANI_CODE_INSTALL_SPEC=<npm-spec>` to install it.
