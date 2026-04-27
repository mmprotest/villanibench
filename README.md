# VillaniBench

VillaniBench is a benchmark scaffold for evaluating **agent runners under fixed backend models**.

Core definition: VillaniBench measures how much reliable agentic work a runner can extract from a fixed backend model under fixed budgets, **relative to a fixed control runner** (`minimal_react_control`).

- `minimal_react_control` is the zero point (score `0.0`).
- VillaniBench Score is control-normalised and relative to control.
- Raw solve rate is reported as diagnostics only.
- **v0 caveat:** `minimal_react_control` is currently a placeholder for harness smoke tests and does not call a backend model.
- **Score validity caveat:** in v0, VillaniBench Score is `diagnostic_only` unless control is replaced with a model-backed comparable run.

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
villanibench compare \
  --runs artifacts/runs/* \
  --control-runner minimal_react_control \
  --output-dir artifacts/comparisons/core_v0_1
```

## Strict vs non-strict

- **Strict**: adapter template can enforce same backend config (model and endpoint assumptions satisfied).
- **Non-strict**: backend config alignment cannot be guaranteed.
- Strict and non-strict runs are not mixed for VillaniBench Score.

## Limitations (v0 scaffold)

- Control adapter is a placeholder and does not call a model.
- Telemetry is mostly partial/null.
- No leaderboard, no Docker, no charts, no web service.

VillaniBench is maintained by creators of Villani Code and should be scrutinized.
