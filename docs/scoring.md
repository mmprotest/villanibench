# Scoring

VillaniBench primary scoring method: `paired_control_adjusted_net_success_v1`.

For each matched tuple `(suite_id, model, budget_profile, comparison_mode, task_id)` between target runner and `minimal_react_control`:

- `success(row) = 1` only when `status == "success"`, else `0`
- `delta = success(target) - success(control)`
- `VillaniBench Score = 100 * mean(delta)`

Interpretation: `+20` means 20 more net successful task completions per 100 comparable attempts than model-backed ReAct control.

Rules:
- Per backend model, supply a matching model-backed control run.
- Strict/non-strict are never mixed.
- Budget profiles are never mixed.
- Missing controls produce partial scores or `not_computed`.
- Duplicate comparable rows are rejected by default.
- CIs use bootstrap by `task_id` (not by row).

Pool separate runs later with:

```bash
villanibench score runs/control-qwen35-9b runs/claude-qwen35-9b runs/control-qwen36-27b runs/claude-qwen36-27b runs/control-qwen36-35b runs/claude-qwen36-35b --output-dir reports/claude-pooled-score
```
