# Runner adapter contract

`RunnerAdapter` interface:
- `prepare(task, sandbox_dir, config)`
- `run(task, sandbox_dir, budget, config) -> AdapterRunResult`
- `collect_telemetry(sandbox_dir) -> Telemetry`
- `cleanup(sandbox_dir)`

External adapters are CLI-template based (`subprocess`) and do not import internals.

## Execution contract

Adapters should execute with cwd set to `sandbox/repo`.

Adapter command templates should only require:
- `prompt_file`
- `cwd`
- `model`
- `base_url`
- `api_key`
- `output_dir`
- `visible_test_command`

Adapters must **not** receive hidden-test paths. Hidden tests are evaluator-only and copied after runner execution.

Command templates are trusted local benchmark configuration and are intentionally simple string templates.

Supported placeholders:
- `{prompt_file}`
- `{prompt_text}`
- `{cwd}`
- `{model}`
- `{base_url}`
- `{api_key}`
- `{output_dir}`
- `{visible_test_command}`

Why no direct imports:
- keep isolation between benchmark and runner internals
- keep adapters symmetric across runners
- avoid privileged integration paths
