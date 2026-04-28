from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

from villanibench.harness.compare import compare_runs
from villanibench.harness.report import generate_report
from villanibench.harness.run import run_suite
from villanibench.tasks.validation import validate_suite_dir, validate_task_dir


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

    vt_p = sub.add_parser("validate-task")
    vt_p.add_argument("task_dir")

    vs_p = sub.add_parser("validate-suite")
    vs_p.add_argument("suite_dir")

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

    if args.cmd == "run":
        if args.runner in {"minimal_react_control", "react"} and not args.base_url:
            raise SystemExit("minimal_react_control requires --base-url because it is model-backed.")
        cfg = {
            "base_url": args.base_url,
            "api_key": args.api_key or "dummy",
            "command_template": _resolve_command_template(args),
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


if __name__ == "__main__":
    main()
