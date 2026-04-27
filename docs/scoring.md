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

Examples:
- control=0.30, runner=0.51 => score=0.30 (captures 30% remaining headroom above control)
- control=0.55, runner=0.69 => score=0.31
- control=0.50, runner=0.25 => score=-0.50

Raw solve rate and related metrics are diagnostics only.
Strict/non-strict runs are separated.
Telemetry in v0 is partial.
