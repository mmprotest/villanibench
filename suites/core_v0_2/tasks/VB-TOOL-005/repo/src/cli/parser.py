def parse_args(argv: list[str]) -> dict:
    return {"dry_run": "--dry-run" in argv, "target": argv[-1] if argv else "default"}
