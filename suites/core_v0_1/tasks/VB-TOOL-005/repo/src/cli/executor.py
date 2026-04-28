def execute(target: str, dry_run: bool = False) -> str:
    return f"DRY {target}" if dry_run else f"WRITE {target}"
