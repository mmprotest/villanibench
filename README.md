# VillaniBench

VillaniBench is a benchmark scaffold for evaluating **agent runners under fixed backend models**.

Core definition: VillaniBench measures how much reliable agentic work a runner can extract from a fixed backend model under fixed budgets, **relative to a fixed control runner** (`minimal_react_control`).

- `minimal_react_control` is the zero point (score `0.0`).
- VillaniBench Score is control-normalised and relative to control.
- Raw solve rate is reported as diagnostics only.

This repository is separate from Villani Code. Villani, OpenCode, and Claude Code are invoked as external CLIs via adapter templates.

## Quick start

```bash
villanibench validate-suite suites/core_v0_1
```

```bash
villanibench run \
  --suite suites/core_v0_1 \
  --runner minimal_react_control \
  --model dummy \
  --output-dir artifacts/runs/control_dummy
```

```bash
villanibench run \
  --suite suites/core_v0_1 \
  --runner villani \
  --model qwen3.6-9b \
  --base-url http://127.0.0.1:1234 \
  --api-key dummy \
  --villani-command-template "villani-code run --prompt-file {prompt_file} --cwd {cwd} --model {model} --base-url {base_url} --api-key {api_key}" \
  --output-dir artifacts/runs/villani_qwen9b
```

```bash
villanibench run \
  --suite suites/core_v0_1 \
  --runner opencode \
  --model qwen3.6-9b \
  --opencode-command-template "opencode run --model {model} --cwd {cwd} --prompt-file {prompt_file}" \
  --output-dir artifacts/runs/opencode_qwen9b
```

```bash
villanibench run \
  --suite suites/core_v0_1 \
  --runner claude_code \
  --model qwen3.6-9b \
  --claude-code-command-template "claude --print --model {model} < {prompt_file}" \
  --output-dir artifacts/runs/claude_code_qwen9b
```

```bash
villanibench compare \
  --runs artifacts/runs/* \
  --control-runner minimal_react_control \
  --output-dir artifacts/comparisons/core_v0_1
```

```bash
villanibench report \
  --comparison artifacts/comparisons/core_v0_1 \
  --output artifacts/reports/core_v0_1.md
```

## Strict vs non-strict

- **Strict**: adapter template can enforce same backend config (model and endpoint assumptions satisfied).
- **Non-strict**: backend config alignment cannot be guaranteed (especially common with default Claude/OpenCode templates).

## Limitations (v0 scaffold)

- Control adapter is a placeholder and does not call a model.
- Telemetry is mostly partial/null.
- No leaderboard, no Docker, no charts, no web service.

VillaniBench is maintained by creators of Villani Code and should be scrutinized.
