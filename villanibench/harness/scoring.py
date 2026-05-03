from __future__ import annotations

import random
import statistics
from collections import defaultdict
from typing import Iterable


SCORING_METHOD = "paired_control_adjusted_net_success_v1"


def is_success(row: dict) -> int:
    return 1 if row.get("status") == "success" else 0


def _pair_key(row: dict) -> tuple:
    return (
        row["suite_id"],
        row["model"],
        row.get("budget_profile", ""),
        row["comparison_mode"],
        row["task_id"],
    )


def _runner_key(row: dict) -> tuple:
    return (row["runner"],) + _pair_key(row)


def bootstrap_task_ci(paired_rows: list[dict], iterations: int = 10_000, seed: int = 0) -> tuple[float, float]:
    if not paired_rows:
        return (0.0, 0.0)
    tasks = sorted({r["task_id"] for r in paired_rows})
    task_to_delta: dict[str, list[int]] = defaultdict(list)
    for row in paired_rows:
        task_to_delta[row["task_id"]].append(row["delta"])
    observed = 100.0 * statistics.mean(r["delta"] for r in paired_rows)
    if len(tasks) <= 1:
        return (observed, observed)
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(iterations):
        sampled = [tasks[rng.randrange(0, len(tasks))] for _ in range(len(tasks))]
        deltas: list[int] = []
        for t in sampled:
            deltas.extend(task_to_delta[t])
        samples.append(100.0 * statistics.mean(deltas))
    samples.sort()
    lo = samples[int(0.025 * (len(samples) - 1))]
    hi = samples[int(0.975 * (len(samples) - 1))]
    return lo, hi


def aggregate_paired_scores(rows: list[dict], control_runner: str = "minimal_react_control") -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    idx: dict[tuple, dict] = {}
    for r in rows:
        k = _runner_key(r)
        if k in idx:
            raise ValueError(f"Duplicate comparable row detected for key={k}")
        idx[k] = r

    group_keys = sorted({(r["runner"], r["suite_id"], r["model"], r.get("budget_profile", ""), r["comparison_mode"]) for r in rows if r["runner"] != control_runner})
    out: list[dict] = []
    for runner, suite_id, model, budget_profile, mode in group_keys:
        runner_rows = [r for r in rows if (r["runner"], r["suite_id"], r["model"], r.get("budget_profile", ""), r["comparison_mode"]) == (runner, suite_id, model, budget_profile, mode)]
        pairs = []
        missing = 0
        non_model_backed = 0
        for rr in runner_rows:
            ck = (control_runner, suite_id, model, budget_profile, mode, rr["task_id"])
            cr = idx.get(ck)
            if cr is None:
                missing += 1
                continue
            if cr.get("control_kind") != "model_backed":
                non_model_backed += 1
                continue
            pairs.append({"task_id": rr["task_id"], "delta": is_success(rr) - is_success(cr), "runner_success": is_success(rr), "control_success": is_success(cr)})

        if not pairs:
            msg = "No comparable model-backed control rows were found."
            if non_model_backed:
                msg = f"{msg} Excluded {non_model_backed} non-model-backed control matches."
            out.append({"runner": runner, "model": model, "suite_id": suite_id, "budget_profile": budget_profile, "comparison_mode": mode, "score_validity": "not_computed", "score_warning": msg, "villanibench_score": None, "paired_task_count": 0, "runner_wins": 0, "control_wins": 0, "ties_success": 0, "ties_failure": 0, "control_solve_rate": 0.0, "runner_solve_rate": 0.0, "absolute_lift": None})
            warnings.append(msg)
            continue
        runner_wins = sum(1 for p in pairs if p["delta"] == 1)
        control_wins = sum(1 for p in pairs if p["delta"] == -1)
        ties_success = sum(1 for p in pairs if p["delta"] == 0 and p["runner_success"] == 1)
        ties_failure = sum(1 for p in pairs if p["delta"] == 0 and p["runner_success"] == 0)
        runner_rate = statistics.mean(p["runner_success"] for p in pairs)
        control_rate = statistics.mean(p["control_success"] for p in pairs)
        score = 100.0 * statistics.mean(p["delta"] for p in pairs)
        warn = None
        if missing:
            warn = f"Missing {missing} matching control rows; score computed from matched rows only."
            warnings.append(warn)
        out.append({"runner": runner, "model": model, "suite_id": suite_id, "budget_profile": budget_profile, "comparison_mode": mode, "score_validity": "valid", "score_warning": warn, "villanibench_score": score, "paired_task_count": len(pairs), "runner_wins": runner_wins, "control_wins": control_wins, "ties_success": ties_success, "ties_failure": ties_failure, "control_solve_rate": control_rate, "runner_solve_rate": runner_rate, "absolute_lift": 100.0 * (runner_rate - control_rate), "_paired_rows": pairs})
    return out, sorted(set(warnings))


def aggregate_overall_paired(vb_by_model: list[dict], iterations: int = 10_000, seed: int = 0) -> list[dict]:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for r in vb_by_model:
        grouped[(r["runner"], r["suite_id"], r.get("budget_profile", ""), r["comparison_mode"])].append(r)
    out: list[dict] = []
    for key, rows in sorted(grouped.items()):
        runner, suite_id, budget_profile, mode = key
        valids = [r for r in rows if r["score_validity"] == "valid"]
        if not valids:
            out.append({"runner": runner, "suite_id": suite_id, "budget_profile": budget_profile, "comparison_mode": mode, "score_validity": "not_computed", "score_warning": "No valid per-model scores.", "villanibench_score": None, "score_ci_low": None, "score_ci_high": None, "ci_method": "task_bootstrap", "ci_iterations": iterations, "models": [], "model_count": 0, "paired_task_count": 0})
            continue
        paired = []
        for r in valids:
            for p in r["_paired_rows"]:
                paired.append({"task_id": p["task_id"], "delta": p["delta"]})
        score = 100.0 * statistics.mean(p["delta"] for p in paired)
        lo, hi = bootstrap_task_ci(paired, iterations=iterations, seed=seed)
        runner_success = sum(p["runner_success"] for r in valids for p in r["_paired_rows"])
        control_success = sum(p["control_success"] for r in valids for p in r["_paired_rows"])
        n = len(paired)
        rr = runner_success / n
        cr = control_success / n
        rel = None if cr == 0 else 100.0 * (rr - cr) / cr
        out.append({"runner": runner, "suite_id": suite_id, "budget_profile": budget_profile, "comparison_mode": mode, "score_validity": "valid", "score_warning": None if rel is not None else "relative_lift is undefined because control_solve_rate is 0.", "villanibench_score": score, "score_ci_low": lo, "score_ci_high": hi, "ci_method": "task_bootstrap", "ci_iterations": iterations, "models": sorted([r["model"] for r in valids]), "model_count": len(valids), "paired_task_count": n, "mean_model_score": statistics.mean(r["villanibench_score"] for r in valids), "backend_stability_stddev": statistics.pstdev(r["villanibench_score"] for r in valids) if len(valids) > 1 else None, "worst_model_score": min(r["villanibench_score"] for r in valids), "best_model_score": max(r["villanibench_score"] for r in valids), "runner_wins": sum(r["runner_wins"] for r in valids), "control_wins": sum(r["control_wins"] for r in valids), "ties_success": sum(r["ties_success"] for r in valids), "ties_failure": sum(r["ties_failure"] for r in valids), "control_solve_rate": cr, "runner_solve_rate": rr, "relative_lift": rel})
    return out
