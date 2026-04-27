# Task authoring

Task contract:
- `task.yaml`, `prompt.txt`, `repo/`, `tests/visible/`, `tests/hidden/`, and oracle JSON files.
- Runner sees prompt + repo + visible tests only.
- Evaluator additionally runs hidden tests and oracle checks.

## Hidden test visibility warning

Hidden tests must not be visible before runner execution. The evaluator copies `tests/hidden/` only after the runner phase completes, so task authors must not rely on hidden tests being present during runner execution.

Calibration guidance:

Tasks should be calibrated so minimal_react_control solves roughly 20% to 60% on approved mid-tier models once the control becomes a real LLM-backed baseline. Tasks solved by everyone or no one are less useful for stable control-normalised scoring.

For v0, minimal_react_control is a placeholder, so stability estimates are diagnostic only.
