# Docker workflow

- **Convenience mode**: harness and agent run in one container (reproducible, not hard isolation).
- **Nested isolation mode**: add `--enable-nested-docker` to run each agent step in a fresh per-task container.

Main Villani Code from GitHub:
```powershell
.\scripts\villanibench-docker.ps1 -Rebuild run `
  --suite suites/core_v0_2 `
  --runner villani `
  --model "villanis/models/qwen3.6-35b-a3b-ud-iq4_xs.gguf" `
  --base-url "http://host.docker.internal:1234" `
  --api-key dummy `
  --output-dir artifacts/runs/villani_35b_core_v0_2_main
```

Local beta Villani Code:
```powershell
.\scripts\villanibench-docker.ps1 -Rebuild -VillaniCodeSource "C:\path\to\villani-code" run `
  --suite suites/core_v0_2 `
  --runner villani `
  --model "villanis/models/qwen3.6-35b-a3b-ud-iq4_xs.gguf" `
  --base-url "http://host.docker.internal:1234" `
  --api-key dummy `
  --output-dir artifacts/runs/villani_35b_core_v0_2_beta
```

Nested hard isolation (WSL/Linux):
```bash
./scripts/villanibench-docker --rebuild --enable-nested-docker run \
  --suite suites/core_v0_2 \
  --runner villani \
  --model "villanis/models/qwen3.6-35b-a3b-ud-iq4_xs.gguf" \
  --base-url "http://host.docker.internal:1234" \
  --api-key dummy \
  --output-dir artifacts/runs/villani_35b_core_v0_2_main_isolated
```

Notes:
- PowerShell wrapper supports convenience Docker mode.
- Hard nested Docker isolation may require WSL because Docker socket mounting is platform-sensitive.
- Native Windows PowerShell fails early for `-EnableNestedDocker` with WSL guidance.
- `host.docker.internal` points from container to host LM Studio.
- Default `--runner villani` installs from GitHub main.
- `-VillaniCodeSource` tests a local beta checkout.
- Output artifacts persist through the repo bind mount.
