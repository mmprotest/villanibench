from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from .scoring import SCORING_METHOD, aggregate_overall_paired, aggregate_paired_scores

RESULT_FILENAMES = ("results.jsonl", "task_results.jsonl", "results.json", "task_results.json")


def _load_rows_from_file(path: Path) -> list[dict]:
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in ("rows", "results", "task_results"):
            if isinstance(payload.get(k), list):
                return payload[k]
    return []


def _discover_result_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            for name in RESULT_FILENAMES:
                files.extend(sorted(p.rglob(name)))
    uniq = []
    seen = set()
    for f in files:
        rp = f.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(f)
    return uniq


def _normalize_rows(files: list[Path]) -> tuple[list[dict], list[str], int]:
    required = ["run_id", "runner", "model", "task_id", "suite_id", "budget_profile", "comparison_mode", "status"]
    rows = []
    warnings = []
    excluded = 0
    for f in files:
        for r in _load_rows_from_file(f):
            n = dict(r)
            n.setdefault("run_id", str(f.parent.name))
            n.setdefault("budget_profile", "")
            n.setdefault("comparison_mode", "strict")
            miss = [k for k in required if k not in n or n.get(k) in (None, "")]
            if n.get("runner") == "minimal_react_control":
                n.setdefault("control_kind", "unknown")
            if miss:
                excluded += 1
                warnings.append(f"Excluded row from {f}: missing fields {miss}")
                continue
            rows.append(n)
    return rows, sorted(set(warnings)), excluded


def _raw_scores(rows: list[dict]) -> list[dict]:
    grouped = {}
    for row in rows:
        key = (row["runner"], row["model"], row["suite_id"], row.get("budget_profile", ""), row["comparison_mode"])
        grouped.setdefault(key, []).append(row)
    out = []
    for key, group in sorted(grouped.items()):
        runner, model, suite_id, budget_profile, mode = key
        valid = [g for g in group if g["status"] not in {"invalid_task", "harness_error"}]
        if not valid:
            continue
        out.append({"runner": runner, "model": model, "suite_id": suite_id, "budget_profile": budget_profile, "comparison_mode": mode, "raw_solve_rate": sum(1 for g in valid if g["status"] == "success") / len(valid), "valid_task_count": len(valid)})
    return out


def compare_runs(run_paths: list[Path], output_dir: Path, control_runner: str = "minimal_react_control") -> dict:
    files = _discover_result_files(run_paths)
    rows, warnings, excluded = _normalize_rows(files)
    vb_by_model, w2 = aggregate_paired_scores(rows, control_runner=control_runner)
    warnings.extend(w2)
    vb_overall = aggregate_overall_paired(vb_by_model)
    for r in vb_by_model:
        r.pop("_paired_rows", None)
    summary = {"scoring_method": SCORING_METHOD, "generated_at": datetime.now(timezone.utc).isoformat(), "control_runner": control_runner, "input_sources": [str(f) for f in files], "loaded_row_count": len(rows), "excluded_row_count": excluded, "raw_scores": _raw_scores(rows), "villanibench_scores_by_model": vb_by_model, "villanibench_scores_overall": vb_overall, "warnings": sorted(set(warnings))}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "comparison_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "REPORT.md").write_text(_render_report(summary), encoding="utf-8")
    if rows:
        with (output_dir / "results_combined.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=sorted({k for row in rows for k in row.keys()}))
            w.writeheader(); w.writerows(rows)
    return summary


def score_pooled(run_paths: list[Path], output_dir: Path, control_runner: str = "minimal_react_control") -> dict:
    summary = compare_runs(run_paths, output_dir, control_runner=control_runner)
    (output_dir / "pooled_score_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "pooled_score_report.md").write_text(_render_report(summary), encoding="utf-8")
    return summary


def _render_report(summary: dict) -> str:
    lines = ["# VillaniBench Score Report", ""]
    lines += ["## Overall VillaniBench Score", "", "| runner | suite_id | budget_profile | comparison_mode | villanibench_score | 95% CI | models | paired_task_count | worst_model_score | score_validity |", "|---|---|---|---|---:|---|---|---:|---:|---|"]
    for r in summary.get("villanibench_scores_overall", []):
        score = "null" if r.get("villanibench_score") is None else f"{r['villanibench_score']:.3f}"
        ci = "n/a" if r.get("score_ci_low") is None else f"[{r['score_ci_low']:.3f}, {r['score_ci_high']:.3f}]"
        lines.append(f"| {r['runner']} | {r['suite_id']} | {r.get('budget_profile','')} | {r['comparison_mode']} | {score} | {ci} | {', '.join(r.get('models',[]))} | {r.get('paired_task_count',0)} | {r.get('worst_model_score','n/a')} | {r.get('score_validity')} |")
    lines += ["", "## Per-model paired breakdown", "", "| runner | model | villanibench_score | control_solve_rate | runner_solve_rate | runner_wins | control_wins | ties_success | ties_failure | paired_task_count |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in summary.get("villanibench_scores_by_model", []):
        s = "null" if r.get("villanibench_score") is None else f"{r['villanibench_score']:.3f}"
        lines.append(f"| {r['runner']} | {r['model']} | {s} | {r.get('control_solve_rate',0):.3f} | {r.get('runner_solve_rate',0):.3f} | {r.get('runner_wins',0)} | {r.get('control_wins',0)} | {r.get('ties_success',0)} | {r.get('ties_failure',0)} | {r.get('paired_task_count',0)} |")
    return "\n".join(lines) + "\n"
