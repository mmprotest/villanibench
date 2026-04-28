# Scoring

VillaniBench Score is the primary metric and is relative to `minimal_react_control`.

For control solve rate `c` and runner solve rate `r`:
- if `r >= c`: `(r - c) / (1 - c)`
- if `r < c`: `(r - c) / c`
- edge cases for `c=0` and `c=1` are handled explicitly.

Category-first aggregation:
1. score per category
2. mean per model
3. mean across models
4. backend stability = stddev across model-level scores

## Score validity

Comparison output includes `score_validity`:
- `valid`: control is model-backed and fully comparable (same suite, model, budget profile, and comparison mode).
- `diagnostic_only`: score computed against legacy placeholder control.
- `not_computed`: no comparable control baseline.

`minimal_react_control` is model-backed by default in v0 and should produce valid scores when runs are comparable.
Legacy results with `control_kind=placeholder` remain readable and are marked `diagnostic_only`.

Strict/non-strict runs are separated and never mixed.

Backend stability is reported as stddev across model-level VillaniBench Scores, with an acceptable variance target of 0.10.

## Status values used in scoring inputs

- `success`
- `hidden_failure`
- `visible_failure`
- `inconsistent_test_result`
- `runner_crash`
- `timeout`
- `forbidden_modification`
- `invalid_task`
- `harness_error`

Runs based on fewer than 30 tasks should be treated as smoke diagnostics, not public benchmark claims.
