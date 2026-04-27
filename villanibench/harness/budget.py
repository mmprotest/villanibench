from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BudgetProfile:
    wall_time_sec: int
    max_model_calls: int
    max_input_tokens: int
    max_output_tokens: int
    max_shell_commands: int
    max_file_reads: int
    max_file_writes: int
    max_patch_attempts: int
    max_context_window_tokens: int
    temperature: int


BUDGETS: dict[str, BudgetProfile] = {
    "lite_v0_1": BudgetProfile(120, 20, 100000, 20000, 20, 80, 10, 5, 32768, 0),
    "standard_v0_1": BudgetProfile(300, 40, 250000, 50000, 40, 120, 20, 10, 32768, 0),
}


def get_budget_profile(name: str) -> BudgetProfile:
    if name not in BUDGETS:
        raise KeyError(f"Unknown budget profile: {name}")
    return BUDGETS[name]
