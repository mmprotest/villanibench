from __future__ import annotations

import fnmatch
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
import difflib

IGNORE_PARTS = {"__pycache__", ".pytest_cache", ".git", "build", "dist", ".venv", "node_modules"}


@dataclass
class DiffStats:
    files_touched: list[str]
    lines_added: int
    lines_deleted: int
    patch_size_lines: int
    tests_modified: bool
    forbidden_file_modified: bool
    expected_file_touched: bool
    decoy_file_touched: bool
    unified_diff: str


def _is_ignored(path: Path) -> bool:
    return any(part in IGNORE_PARTS for part in path.parts)


def snapshot_files(root: Path) -> dict[str, str]:
    snap: dict[str, str] = {}
    for p in root.rglob("*"):
        if not p.is_file() or _is_ignored(p):
            continue
        rel = p.relative_to(root).as_posix()
        snap[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return snap


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def analyze_diff(before: dict[str, str], after: dict[str, str], sandbox_root: Path, task_dir: Path, diff_output: Path) -> DiffStats:
    changed = sorted(set(before) | set(after))
    touched = [p for p in changed if before.get(p) != after.get(p)]
    all_diff_lines: list[str] = []
    adds = dels = 0
    for rel in touched:
        bp = sandbox_root / rel
        # best effort text diff
        if bp.exists():
            after_lines = bp.read_text(encoding="utf-8", errors="ignore").splitlines()
        else:
            after_lines = []
        # cannot reconstruct before content; use empty placeholder for hash-based snapshots v0
        before_lines: list[str] = []
        udiff = list(difflib.unified_diff(before_lines, after_lines, fromfile=f"a/{rel}", tofile=f"b/{rel}", lineterm=""))
        all_diff_lines.extend(udiff)
        for line in udiff:
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("+"):
                adds += 1
            elif line.startswith("-"):
                dels += 1

    diff_text = "\n".join(all_diff_lines) + ("\n" if all_diff_lines else "")
    diff_output.write_text(diff_text, encoding="utf-8")

    oracle = task_dir / "oracle"
    allowed = _load_json(oracle / "allowed_files.json")
    expected = _load_json(oracle / "expected_files.json")
    failure_modes = _load_json(oracle / "failure_modes.json")

    forbidden_files = set(allowed.get("forbidden_files", []))
    forbidden_patterns = allowed.get("forbidden_patterns", [])
    forbidden = False
    for rel in touched:
        if rel in forbidden_files:
            forbidden = True
        for pat in forbidden_patterns:
            if pat in rel or fnmatch.fnmatch(rel, pat):
                forbidden = True

    expected_files = set(expected.get("expected_files", [])) | set(expected.get("strongly_expected_files", []))
    expected_touched = any(r.startswith("repo/") and r.removeprefix("repo/") in expected_files for r in touched)

    decoys = set(failure_modes.get("decoy_files", []))
    decoy_touched = any(r.startswith("repo/") and r.removeprefix("repo/") in decoys for r in touched)

    tests_modified = any(r.startswith("tests/") or "/tests/" in r for r in touched)

    return DiffStats(
        files_touched=touched,
        lines_added=adds,
        lines_deleted=dels,
        patch_size_lines=adds + dels,
        tests_modified=tests_modified,
        forbidden_file_modified=forbidden,
        expected_file_touched=expected_touched,
        decoy_file_touched=decoy_touched,
        unified_diff=diff_text,
    )
