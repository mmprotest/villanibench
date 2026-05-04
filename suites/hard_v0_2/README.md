# VillaniBench Hard v0.1

A harder 30-task suite for evaluating runner quality under a fixed backend model.

Categories:

- 5 minimal_patch tasks
- 5 localisation tasks
- 5 verification tasks
- 5 state_coherence tasks
- 5 tool_efficiency tasks
- 5 recovery tasks

This suite is intentionally more adversarial than `core_v0_1`: it uses decoy files, hidden edge cases, multi-file consistency fixes, registry/discovery noise, and false-cause recovery traps.

Before using results, run:

```bash
villanibench validate-suite suites/hard_v0_1
villanibench validate-behavior suites/hard_v0_1
```

The design target is that a strong 35B local model with `minimal_react_control` should not saturate the suite.
