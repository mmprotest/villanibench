# Runner adapter contract

`RunnerAdapter` interface:
- `prepare(task, sandbox_dir, config)`
- `run(task, sandbox_dir, budget, config) -> AdapterRunResult`
- `collect_telemetry(sandbox_dir) -> Telemetry`
- `cleanup(sandbox_dir)`

External adapters are CLI-template based (`subprocess`) and do not import internals.
`minimal_react_control` is internal and model-backed (OpenAI-compatible chat completions).

## Execution contract

Adapters should execute with cwd set to `sandbox/repo`.

Adapter command templates should only require:
- `prompt_file`
- `prompt_text`
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


`{prompt_text}` is for CLIs that take the instruction as positional text. `{prompt_file}` should only be used if a CLI explicitly supports prompt-file input.

External CLI adapters run with UTF-8-safe environment defaults (`PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`).

Diff analysis should ignore known runner bookkeeping directories (for example `.villani/`, `.villani_code/`) so patch metrics reflect task-solution edits only.
