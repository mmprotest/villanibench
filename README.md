# VillaniBench

VillaniBench is a benchmark scaffold for evaluating **agent runners under fixed backend models**.

Core definition: VillaniBench measures how much reliable agentic work a runner can extract from a fixed backend model under fixed budgets, **relative to a fixed control runner** (`minimal_react_control`).

- `minimal_react_control` is the zero point (score `0.0`).
- VillaniBench Score is control-normalised and relative to control.
- Raw solve rate is reported as diagnostics only.
- `minimal_react_control` is a real model-backed control runner.
- VillaniBench Score is valid only with a matching model-backed control run.

This repository is separate from Villani Code. Villani, OpenCode, and Claude Code are invoked as external CLIs via adapter templates.

## Quick start

```bash
villanibench validate-suite suites/core_v0_1
```

```bash
villanibench run \
  --suite suites/core_v0_1 \
  --runner minimal_react_control \
  --model qwen3.6-9b \
  --base-url http://127.0.0.1:1234 \
  --api-key dummy \
  --output-dir artifacts/runs/control_qwen9b
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
villanibench compare \
  --runs artifacts/runs/control_qwen9b artifacts/runs/villani_qwen9b \
  --control-runner minimal_react_control \
  --output-dir artifacts/comparisons/qwen9b
```

## Strict vs non-strict

- **Strict**: adapter template can enforce same backend config (model and endpoint assumptions satisfied).
- **Non-strict**: backend config alignment cannot be guaranteed.
- Strict and non-strict runs are not mixed for VillaniBench Score.

## Limitations (v0 scaffold)

- Telemetry can be partial depending on backend usage fields.
- No leaderboard, no Docker, no charts, no web service.

VillaniBench is maintained by creators of Villani Code and should be scrutinized.
