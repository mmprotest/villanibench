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
- `diagnostic_only`: score computed against placeholder control.
- `not_computed`: no comparable control baseline.

In v0, `minimal_react_control` is placeholder/non-model-backed, so scores are expected to be `diagnostic_only` unless replaced by a model-backed control adapter.

Strict/non-strict runs are separated and never mixed.

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
