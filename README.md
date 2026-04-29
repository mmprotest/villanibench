# VillaniBench

VillaniBench is a benchmark scaffold for evaluating **agent runners under fixed backend models**.

Core definition: VillaniBench measures how much reliable agentic work a runner can extract from a fixed backend model under fixed budgets, **relative to a fixed control runner** (`minimal_react_control`).

- `minimal_react_control` is the zero point (score `0.0`).
- VillaniBench Score is control-normalised and relative to control.
- Raw solve rate is reported as diagnostics only.
- `minimal_react_control` is a real model-backed control runner and requires `--base-url` for runs.
- VillaniBench Score is valid only with a matching model-backed control run.

This repository is separate from Villani Code. Villani, OpenCode, and Claude Code are invoked as external CLIs via adapter templates.

## Quick start

```bash
villanibench validate-suite suites/core_v0_1
```

```bash
villanibench validate-behavior suites/core_v0_1
```

Recommended pre-run sequence:

```bash
python -m pytest -q
villanibench validate-suite suites/core_v0_1
villanibench validate-behavior suites/core_v0_1
```

Structural and behavioural validation are different:
- structural validation checks schema/files and task packaging
- behavioural validation checks visible+hidden tests fail before any fix

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
  --villani-command-template "villani-code run --repo {cwd} --provider openai --model {model} --base-url {base_url} --api-key {api_key} --auto-approve --auto-accept-edits --dangerously-skip-permissions --plan-mode off --no-stream "{prompt_text}"" \
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

## Limitations (v0.1 scaffold)

- The core v0.1 suite currently includes 10 tasks total:
  - 5 `minimal_patch` tasks
  - 5 `localisation` tasks
- This is still too small for strong public benchmark claims; treat results as development diagnostics.
- Next planned categories are `verification`, `state_coherence`, `tool_efficiency`, and `recovery`.

- Telemetry can be partial depending on backend usage fields.
- No leaderboard, no Docker, no charts, no web service.

VillaniBench is maintained by creators of Villani Code and should be scrutinized.


Notes for external CLI adapters:
- VillaniBench sets subprocess cwd to the sandbox repo (`sandbox/repo`).
- Villani Code should be passed `--repo "{cwd}"` (Villani supports `--repo`).
- Use `{prompt_text}` for positional instruction CLIs; do not assume `--prompt-file` support.
- VillaniBench sets `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1` for external runner subprocesses to avoid Windows Unicode console crashes.
