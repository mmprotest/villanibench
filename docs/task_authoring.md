# Task authoring

Task contract:
- `task.yaml`, `prompt.txt`, `repo/`, `tests/visible/`, `tests/hidden/`, and oracle JSON files.
- Runner sees prompt + repo + visible tests only.
- Evaluator additionally runs hidden tests and oracle checks.

## Hidden test visibility warning

Hidden tests must not be visible before runner execution. The evaluator copies `tests/hidden/` only after the runner phase completes, so task authors must not rely on hidden tests being present during runner execution.

Calibration guidance:

Tasks should be calibrated so minimal_react_control solves roughly 20% to 60% on approved mid-tier models. Tasks solved by everyone or no one are less useful for stable control-normalised scoring.

For `minimal_patch` tasks, keep the reference patch small and typically target one expected source file in `oracle/expected_files.json`.

For `localisation` tasks:
- Include at least one plausible decoy file that looks relevant but should not be patched.
- Make the expected file discoverable through call-chain/code reading, not by naming it in the prompt.
- Keep hidden tests focused on a different edge case than visible tests.
- Include `edited_decoy_file` in `oracle/failure_modes.json` and list decoy paths in `decoy_files` metadata when possible.

## Behavioural requirements

- Visible tests must fail before any fix is applied.
- Hidden tests must fail before any fix is applied.
- Hidden tests must include at least one hidden bug-revealing case, not only preservation cases.
- Avoid mathematically commutative bug setups that make hidden cases meaningless (for example percentage discount/tax order can commute); prefer non-commutative setups such as fixed discount amount then tax.
