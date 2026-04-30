# Methodology

VillaniBench compares runners on the same task, same backend model, and same budget.

- Runner quality is measured relative to a fixed control runner (`minimal_react_control`).
- The model-backed control runner is the zero point.
- Raw solve rate is diagnostic only.
- Strict and non-strict comparisons are reported separately.
- Every backend/model combination needs its own control baseline.
- Conflict disclosure: benchmark authors may also build runners; results should be independently scrutinized.

## Runner-visible contract and hidden-test isolation

Before runner execution, the sandbox must expose only:
- `prompt.txt`
- `repo/`
- `tests/visible/`

`tests/hidden/` is copied in **only after** the runner has finished and post-run visible evaluation has been completed. This prevents hidden-test leakage to runners that inspect the filesystem during execution.

Diff and patch-size analysis is computed only from `repo/` and `tests/visible/` snapshots around runner execution.

Current core v0.1 coverage includes `minimal_patch`, `localisation`, `verification`, `state_coherence`, `tool_efficiency`, and `recovery`.

## Behavioural validation

Use `villanibench validate-behavior <suite_path>` to verify each task is behaviourally valid before benchmark runs. This evaluator-only check runs task visible tests and hidden tests in a temporary sandbox before any fix and requires both to fail without timeout.


Runner bookkeeping artifacts (for example `.villani/` and `.villani_code/`) are excluded from diff-based metrics (`files_touched`, `final.diff`, `patch_size_lines`) so runners are not penalized for trace/checkpoint files unrelated to the solution patch.
