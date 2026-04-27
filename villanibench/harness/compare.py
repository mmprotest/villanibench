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
        key = (row["runner"], row["model"], row["suite_id"], row["comparison_mode"])
        keyed.setdefault(key, []).append(row)

    warnings: list[str] = []
    for (runner, model, suite_id, mode), group in keyed.items():
        valid = [g for g in group if g["status"] not in {"invalid_task", "harness_error"}]
        if not valid:
            continue
        raw = sum(1 for g in valid if g["status"] == "success") / len(valid)
        raw_scores.append({
            "runner": runner,
            "model": model,
            "suite_id": suite_id,
            "comparison_mode": mode,
            "raw_solve_rate": raw,
            "valid_task_count": len(valid),
        })

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
        fields = sorted(rows[0].keys())
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    report_md = output_dir / "REPORT.md"
    report_md.write_text(_render_report(summary), encoding="utf-8")
    return summary


def _render_report(summary: dict) -> str:
    lines = ["# VillaniBench Comparison Report", ""]
    lines += ["## VillaniBench Score (main)", "", "| Runner | Suite | Mode | Mean Score |", "|---|---|---|---|"]
    for row in summary["villanibench_scores_overall"]:
        lines.append(f"| {row['runner']} | {row['suite_id']} | {row['comparison_mode']} | {row['mean_villanibench_score']:.3f} |")
    lines += ["", "## Backend stability", "", "| Runner | Mode | Stddev | Target |", "|---|---|---|---|"]
    for row in summary["villanibench_scores_overall"]:
        lines.append(f"| {row['runner']} | {row['comparison_mode']} | {row['backend_stability_stddev']:.3f} | {row['acceptable_variance_target']:.2f} |")
    lines += ["", "## Category breakdown", ""]
    for row in summary["villanibench_scores_by_model"]:
        lines.append(f"### {row['runner']} / {row['model']} / {row['comparison_mode']}")
        lines.append("| Category | Control | Runner | Score |")
        lines.append("|---|---:|---:|---:|")
        for c in row["category_scores"]:
            lines.append(f"| {c['category']} | {c['control_solve_rate']:.3f} | {c['runner_solve_rate']:.3f} | {c['villanibench_score']:.3f} |")
        lines.append("")
    lines += ["## Raw solve rate diagnostics (diagnostic only)", "", "| Runner | Model | Mode | Raw solve rate | n |", "|---|---|---|---:|---:|"]
    for row in summary["raw_scores"]:
        lines.append(f"| {row['runner']} | {row['model']} | {row['comparison_mode']} | {row['raw_solve_rate']:.3f} | {row['valid_task_count']} |")
    lines += ["", "## Warnings", ""]
    for w in summary.get("warnings", []):
        lines.append(f"- {w}")
    return "\n".join(lines) + "\n"
