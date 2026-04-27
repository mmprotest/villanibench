# Methodology

VillaniBench compares runners on the same task, same backend model, and same budget.

- Runner quality is measured relative to a fixed control runner (`minimal_react_control`).
- The control runner is the zero point.
- Raw solve rate is diagnostic only.
- Strict and non-strict comparisons are reported separately.
- Conflict disclosure: benchmark authors may also build runners; results should be independently scrutinized.

VillaniBench is designed so the benchmark score is relative to the control runner under the same backend. Because each backend gets its own control baseline, the resulting runner score is intended to be stable across approved backend models within acceptable variance.
