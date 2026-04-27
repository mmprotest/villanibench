from __future__ import annotations

import statistics
from collections import defaultdict


def villanibench_category_score(control: float, runner: float) -> float:
    if control == 1.0 and runner == 1.0:
        return 0.0
    if runner >= control:
        if control == 1.0:
            return (runner - control) / control
        if control == 0.0:
            return runner
        return (runner - control) / (1 - control)
    if control == 0.0:
        return 0.0
    return (runner - control) / control


def aggregate_model_category_scores(rows: list[dict], control_runner: str = "minimal_react_control") -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        grouped[(r["suite_id"], r["model"], r.get("budget_profile", ""), r["comparison_mode"], r["runner"])].append(r)

    control_index: dict[tuple, list[dict]] = {
        (k[0], k[1], k[2], k[3]): v for k, v in grouped.items() if k[4] == control_runner
    }

    available_modes: dict[tuple, set[str]] = defaultdict(set)
    for (suite_id, model, budget_profile, mode, runner), _ in grouped.items():
        if runner == control_runner:
            available_modes[(suite_id, model, budget_profile)].add(mode)

    outputs: list[dict] = []
    for (suite_id, model, budget_profile, mode, runner), runner_rows in grouped.items():
        if runner == control_runner:
            continue
        control_rows = control_index.get((suite_id, model, budget_profile, mode))
        if not control_rows:
            modes = available_modes.get((suite_id, model, budget_profile), set())
            mode_warning = None
            if modes:
                sampled_mode = sorted(modes)[0]
                mode_warning = (
                    f"Runner {runner} has comparison_mode={mode} but available minimal_react_control run has "
                    f"comparison_mode={sampled_mode}; VillaniBench Score not computed."
                )
                warnings.append(mode_warning)
            else:
                warnings.append("No matching minimal_react_control run found; VillaniBench Score not computed.")
            outputs.append({
                "runner": runner,
                "model": model,
                "suite_id": suite_id,
                "budget_profile": budget_profile,
                "comparison_mode": mode,
                "category_scores": [],
                "model_villanibench_score": None,
                "score_validity": "not_computed",
                "score_warning": mode_warning or "No matching minimal_react_control run found; VillaniBench Score not computed.",
            })
            continue

        control_kind = control_rows[0].get("control_kind")
        score_validity = "valid" if control_kind == "model_backed" else "diagnostic_only"
        score_warning = None
        if score_validity == "diagnostic_only":
            score_warning = (
                "VillaniBench Score is diagnostic only because minimal_react_control is a placeholder "
                "and does not call the backend model."
            )
            warnings.append(score_warning)

        categories = sorted({r["category"] for r in runner_rows})
        category_scores = []
        for c in categories:
            rr = [x for x in runner_rows if x["category"] == c and x["status"] not in {"invalid_task", "harness_error"}]
            cr = [x for x in control_rows if x["category"] == c and x["status"] not in {"invalid_task", "harness_error"}]
            task_ids = {x["task_id"] for x in rr} & {x["task_id"] for x in cr}
            rr = [x for x in rr if x["task_id"] in task_ids]
            cr = [x for x in cr if x["task_id"] in task_ids]
            if not rr or not cr:
                continue
            rs = sum(1 for x in rr if x["status"] == "success") / len(rr)
            cs = sum(1 for x in cr if x["status"] == "success") / len(cr)
            category_scores.append({
                "category": c,
                "control_solve_rate": cs,
                "runner_solve_rate": rs,
                "villanibench_score": villanibench_category_score(cs, rs),
                "valid_task_count": len(rr),
            })

        model_score = statistics.mean([c["villanibench_score"] for c in category_scores]) if category_scores else None
        outputs.append({
            "runner": runner,
            "model": model,
            "suite_id": suite_id,
            "budget_profile": budget_profile,
            "comparison_mode": mode,
            "category_scores": category_scores,
            "model_villanibench_score": model_score,
            "score_validity": score_validity if model_score is not None else "not_computed",
            "score_warning": score_warning if model_score is not None else "No overlapping valid tasks with control; VillaniBench Score not computed.",
        })
    return outputs, sorted(set(warnings))


def aggregate_overall(vb_by_model: list[dict], target_stddev: float = 0.10) -> list[dict]:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in vb_by_model:
        if row["model_villanibench_score"] is None:
            continue
        grouped[(row["runner"], row["suite_id"], row.get("budget_profile", ""), row["comparison_mode"], row.get("score_validity", "not_computed"))].append(row)

    out = []
    for (runner, suite_id, budget_profile, mode, score_validity), rows in grouped.items():
        scores = [r["model_villanibench_score"] for r in rows]
        out.append({
            "runner": runner,
            "suite_id": suite_id,
            "budget_profile": budget_profile,
            "comparison_mode": mode,
            "score_validity": score_validity,
            "mean_villanibench_score": statistics.mean(scores),
            "backend_stability_stddev": statistics.pstdev(scores) if len(scores) > 1 else 0.0,
            "models": [r["model"] for r in rows],
            "acceptable_variance_target": target_stddev,
        })
    return out
