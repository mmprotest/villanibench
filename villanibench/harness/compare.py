from __future__ import annotations

import csv
import json
from pathlib import Path

from .scoring import aggregate_model_category_scores, aggregate_overall


def _read_results_jsonl(run_dir: Path) -> list[dict]:
    path = run_dir / "results.jsonl"
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def compare_runs(run_paths: list[Path], output_dir: Path, control_runner: str = "minimal_react_control") -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for p in run_paths:
        rows.extend(_read_results_jsonl(p))

    raw_scores = []
    keyed: dict[tuple, list[dict]] = {}
    for row in rows:
        key = (row["runner"], row["model"], row["suite_id"], row.get("budget_profile", ""), row["comparison_mode"])
        keyed.setdefault(key, []).append(row)

    warnings: list[str] = []
    for (runner, model, suite_id, budget_profile, mode), group in keyed.items():
        valid = [g for g in group if g["status"] not in {"invalid_task", "harness_error"}]
        if not valid:
            continue
        raw = sum(1 for g in valid if g["status"] == "success") / len(valid)
        visible_solve_rate = sum(1 for g in valid if g.get("success_visible")) / len(valid)
        hidden_solve_rate = sum(1 for g in valid if g.get("success_hidden")) / len(valid)
        timeout_rate = sum(1 for g in valid if g.get("status") == "timeout") / len(valid)
        crash_rate = sum(1 for g in valid if g.get("status") == "runner_crash") / len(valid)
        forbidden_modification_rate = sum(1 for g in valid if g.get("forbidden_file_modified")) / len(valid)
        test_modification_rate = sum(1 for g in valid if g.get("tests_modified")) / len(valid)
        raw_scores.append({
            "runner": runner,
            "model": model,
            "suite_id": suite_id,
            "budget_profile": budget_profile,
            "comparison_mode": mode,
            "raw_solve_rate": raw,
            "visible_solve_rate": visible_solve_rate,
            "hidden_solve_rate": hidden_solve_rate,
            "timeout_rate": timeout_rate,
            "crash_rate": crash_rate,
            "forbidden_modification_rate": forbidden_modification_rate,
            "test_modification_rate": test_modification_rate,
            "valid_task_count": len(valid),
        })
        for g in valid:
            for setting_warning in g.get("setting_warnings", []):
                warnings.append(setting_warning)

    vb_by_model, vb_warnings = aggregate_model_category_scores(rows, control_runner=control_runner)
    warnings.extend(vb_warnings)
    if not any(r.get("runner") != control_runner for r in rows):
        warnings.append("No non-control runs found; VillaniBench score not computed.")
    vb_overall = aggregate_overall(vb_by_model)

    summary = {
        "control_runner": control_runner,
        "raw_scores": raw_scores,
        "villanibench_scores_by_model": vb_by_model,
        "villanibench_scores_overall": vb_overall,
        "warnings": sorted(set(warnings)),
    }

    (output_dir / "comparison_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    csv_path = output_dir / "results_combined.csv"
    if rows:
        fields = sorted({k for row in rows for k in row.keys()})
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    report_md = output_dir / "REPORT.md"
    report_md.write_text(_render_report(summary), encoding="utf-8")
    return summary


def _render_report(summary: dict) -> str:
    lines = ["# VillaniBench Comparison Report", ""]
    vb_rows = summary.get("villanibench_scores_by_model", [])
    has_valid_score = any(row.get("score_validity") == "valid" and row.get("model_villanibench_score") is not None for row in vb_rows)
    has_only_diagnostic_scores = bool(vb_rows) and all(row.get("score_validity") == "diagnostic_only" for row in vb_rows)

    if not has_valid_score:
        lines.append("No valid VillaniBench Score is available for this comparison. See raw diagnostics below.")
        lines.append("")
    if has_only_diagnostic_scores:
        lines.append("Only diagnostic VillaniBench Scores are available. Do not treat this as a valid benchmark ranking.")
        lines.append("")

    lines += [
        "## VillaniBench Score",
        "",
        "This is the main score.",
        "It is relative to `minimal_react_control`.",
        "Raw solve rate is diagnostic only.",
        "",
        "| runner | model | suite_id | budget_profile | comparison_mode | score_validity | VillaniBench Score | backend_stability_stddev | raw_solve_rate | valid_task_count |",
        "|---|---|---|---|---|---|---:|---|---:|---:|",
    ]

    raw_index = {
        (r["runner"], r["model"], r["suite_id"], r.get("budget_profile", ""), r["comparison_mode"]): r
        for r in summary["raw_scores"]
    }
    for row in vb_rows:
        raw = raw_index.get(
            (row["runner"], row["model"], row["suite_id"], row.get("budget_profile", ""), row["comparison_mode"]),
            {},
        )
        score = row["model_villanibench_score"]
        score_text = "null" if score is None else f"{score:.3f}"
        lines.append(
            f"| {row['runner']} | {row['model']} | {row['suite_id']} | {row.get('budget_profile', '')} | {row['comparison_mode']} | "
            f"{row.get('score_validity', 'not_computed')} | {score_text} | n/a | "
            f"{raw.get('raw_solve_rate', 0.0):.3f} | {raw.get('valid_task_count', 0)} |"
        )

    lines += ["", "## Score validity", "", "- `valid`: score is control-normalized using a comparable model-backed control run."]
    lines.append("- `diagnostic_only`: score is computed against placeholder control and should not be used for ranking.")
    lines.append("- `not_computed`: no comparable control baseline exists.")

    if vb_rows and all(
        row.get("score_validity") in {"diagnostic_only", "not_computed"} for row in vb_rows
    ):
        lines += [
            "",
            "**Warning:** all VillaniBench Scores are diagnostic or missing, so this report is not a benchmark ranking.",
        ]

    lines += ["", "## Backend stability", ""]
    lines += [
        "| runner | models | mean_villanibench_score | backend_stability_stddev | acceptable_variance_target | stable? |",
        "|---|---|---:|---|---:|---|",
    ]
    for row in summary.get("villanibench_scores_overall", []):
        stddev = "insufficient_models" if row.get("backend_stability_stddev") is None else f"{row['backend_stability_stddev']:.3f}"
        lines.append(
            f"| {row['runner']} | {', '.join(row['models'])} | {row['mean_villanibench_score']:.3f} | {stddev} | "
            f"{row['acceptable_variance_target']:.2f} | {row.get('stable', 'insufficient_models')} |"
        )

    lines += ["", "## Category breakdown", ""]
    lines += [
        "| runner | model | category | control_solve_rate | runner_solve_rate | villanibench_score | valid_task_count |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for row in summary["villanibench_scores_by_model"]:
        for c in row["category_scores"]:
            lines.append(
                f"| {row['runner']} | {row['model']} | {c['category']} | {c['control_solve_rate']:.3f} | "
                f"{c['runner_solve_rate']:.3f} | {c['villanibench_score']:.3f} | {c['valid_task_count']} |"
            )

    lines += ["", "## Raw solve-rate diagnostics", ""]
    lines += [
        "| runner | model | suite_id | budget_profile | comparison_mode | raw_solve_rate | visible_solve_rate | hidden_solve_rate | timeout_rate | crash_rate | forbidden_modification_rate | test_modification_rate |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["raw_scores"]:
        lines.append(
            f"| {row['runner']} | {row['model']} | {row['suite_id']} | {row.get('budget_profile', '')} | {row['comparison_mode']} | {row['raw_solve_rate']:.3f} | {row['visible_solve_rate']:.3f} | "
            f"{row['hidden_solve_rate']:.3f} | {row['timeout_rate']:.3f} | {row['crash_rate']:.3f} | "
            f"{row['forbidden_modification_rate']:.3f} | {row['test_modification_rate']:.3f} |"
        )

    lines += ["", "## Warnings", ""]
    for w in summary.get("warnings", []):
        lines.append(f"- {w}")
    return "\n".join(lines) + "\n"
