from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

from villanibench.harness.compare import compare_runs, score_pooled
from villanibench.harness.report import generate_report
from villanibench.harness.run import run_suite
from villanibench.tasks.validation import validate_suite_behavior, validate_suite_dir, validate_task_dir


def _add_common_runner_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--runner-command-template")
    p.add_argument("--villani-command-template")
    p.add_argument("--opencode-command-template")
    p.add_argument("--claude-code-command-template")


def _resolve_command_template(args) -> str | None:
    if args.runner == "villani" and args.villani_command_template:
        return args.villani_command_template
    if args.runner == "opencode" and args.opencode_command_template:
        return args.opencode_command_template
    if args.runner == "claude_code" and args.claude_code_command_template:
        return args.claude_code_command_template
    return args.runner_command_template


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="villanibench")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run")
    run_p.add_argument("--suite", required=True)
    run_p.add_argument("--runner", required=True)
    run_p.add_argument("--model", required=True)
    run_p.add_argument("--base-url")
    run_p.add_argument("--api-key")
    run_p.add_argument("--output-dir", required=True)
    _add_common_runner_args(run_p)

    cmp_p = sub.add_parser("compare")
    cmp_p.add_argument("--runs", nargs="+", required=True)
    cmp_p.add_argument("--control-runner", default="minimal_react_control")
    cmp_p.add_argument("--output-dir", required=True)

    rep_p = sub.add_parser("report")
    rep_p.add_argument("--comparison", required=True)
    rep_p.add_argument("--output", required=True)

    score_p = sub.add_parser("score")
    score_p.add_argument("inputs", nargs="+")
    score_p.add_argument("--control-runner", default="minimal_react_control")
    score_p.add_argument("--output-dir", required=True)

    vt_p = sub.add_parser("validate-task")
    vt_p.add_argument("task_dir")

    vs_p = sub.add_parser("validate-suite")
    vs_p.add_argument("suite_dir")
    vb_p = sub.add_parser("validate-behavior")
    vb_p.add_argument("suite_dir")
    vb_p.add_argument("--timeout-sec", type=int, default=20)

    args = parser.parse_args(argv)

    if args.cmd == "validate-task":
        errs = validate_task_dir(Path(args.task_dir))
        if errs:
            print("INVALID")
            for e in errs:
                print(f"- {e}")
            raise SystemExit(1)
        print("OK")
        return

    if args.cmd == "validate-suite":
        errs = validate_suite_dir(Path(args.suite_dir))
        if errs:
            print("INVALID")
            for e in errs:
                print(f"- {e}")
            raise SystemExit(1)
        print("OK")
        return
    if args.cmd == "validate-behavior":
        if args.timeout_sec <= 0:
            raise SystemExit("--timeout-sec must be a positive integer.")
        ok, rows = validate_suite_behavior(Path(args.suite_dir), timeout_sec=args.timeout_sec)
        for row in rows:
            if row["ok"]:
                print(f"{row['task_id']}: OK visible_pre_fails=true hidden_pre_fails=true")
            else:
                issues: list[str] = []
                if not row["visible_pre_fails"]:
                    issues.append("visible tests passed before fix")
                if not row["hidden_pre_fails"]:
                    issues.append("hidden tests passed before fix")
                if row["visible_timed_out"]:
                    issues.append("visible test command timed out")
                if row["hidden_timed_out"]:
                    issues.append("hidden test command timed out")
                if row.get("message"):
                    issues.append(str(row["message"]))
                print(f"{row['task_id']}: FAIL {'; '.join(issues)}")
        report_dir = Path("artifacts/validation")
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / "behavior_summary.json").write_text(json.dumps({"suite": args.suite_dir, "results": rows}, indent=2), encoding="utf-8")
        if not ok:
            raise SystemExit(1)
        return

    if args.cmd == "run":
        if args.runner in {"minimal_react_control", "react"} and not args.base_url:
            raise SystemExit("minimal_react_control requires --base-url because it is model-backed.")
        cfg = {
            "base_url": args.base_url,
            "api_key": args.api_key or "dummy",
            "command_template": _resolve_command_template(args),
            "log_progress": True,
        }
        summary = run_suite(Path(args.suite), args.runner, args.model, Path(args.output_dir), cfg)
        print(json.dumps(summary, indent=2))
        return

    if args.cmd == "compare":
        run_paths: list[Path] = []
        for pattern in args.runs:
            matches = [Path(p) for p in glob.glob(pattern)]
            if matches:
                run_paths.extend(matches)
            else:
                run_paths.append(Path(pattern))
        summary = compare_runs(run_paths, Path(args.output_dir), control_runner=args.control_runner)
        print(json.dumps(summary, indent=2))
        return

    if args.cmd == "report":
        generate_report(Path(args.comparison), Path(args.output))
        print(f"Wrote {args.output}")
        return

    if args.cmd == "score":
        inputs=[Path(x) for x in args.inputs]
        summary=score_pooled(inputs, Path(args.output_dir), control_runner=args.control_runner)
        print(json.dumps(summary, indent=2))
        return


if __name__ == "__main__":
    main()
