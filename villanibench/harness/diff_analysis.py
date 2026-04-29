from __future__ import annotations

import difflib
import fnmatch
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

IGNORE_PARTS = {"__pycache__", ".pytest_cache", ".git", "build", "dist", ".venv", "venv", "node_modules", ".villani", ".villani_code"}
IGNORE_SUFFIXES = {".pyc"}
IGNORE_PATTERNS = {"*.egg-info", ".coverage", ".coverage.*", "coverage.xml"}
MAX_TEXT_SNAPSHOT_BYTES = 512_000


@dataclass
class FileSnapshot:
    hash: str
    text_lines: list[str] | None
    is_binary_or_large: bool


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
    if any(part in IGNORE_PARTS for part in path.parts):
        return True
    if path.suffix in IGNORE_SUFFIXES:
        return True
    return any(fnmatch.fnmatch(path.name, pattern) for pattern in IGNORE_PATTERNS)


def _read_text_lines(path: Path) -> tuple[list[str] | None, bool]:
    raw = path.read_bytes()
    if len(raw) > MAX_TEXT_SNAPSHOT_BYTES or b"\x00" in raw:
        return None, True
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, True
    return text.splitlines(), False


def snapshot_files(root: Path, include_roots: tuple[str, ...] = ("repo", "tests/visible")) -> dict[str, FileSnapshot]:
    snap: dict[str, FileSnapshot] = {}
    for include_root in include_roots:
        start = root / include_root
        if not start.exists():
            continue
        for p in start.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(root)
            if _is_ignored(rel):
                continue
            rel_key = rel.as_posix()
            file_hash = hashlib.sha256(p.read_bytes()).hexdigest()
            text_lines, is_binary_or_large = _read_text_lines(p)
            snap[rel_key] = FileSnapshot(hash=file_hash, text_lines=text_lines, is_binary_or_large=is_binary_or_large)
    return snap


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def analyze_diff(
    before: dict[str, FileSnapshot],
    after: dict[str, FileSnapshot],
    task_dir: Path,
    diff_output: Path,
) -> DiffStats:
    def is_test_path(rel: str) -> bool:
        return (
            rel.startswith("tests/")
            or "/tests/" in rel
            or "\\tests\\" in rel
            or rel.startswith("repo/tests/")
            or rel.startswith("tests/visible/")
            or rel.startswith("tests/hidden/")
        )

    changed = sorted(set(before) | set(after))
    touched = [p for p in changed if before.get(p) != after.get(p)]
    all_diff_lines: list[str] = []
    adds = dels = 0
    for rel in touched:
        before_file = before.get(rel)
        after_file = after.get(rel)
        before_lines = before_file.text_lines if before_file else []
        after_lines = after_file.text_lines if after_file else []
        before_special = before_file and before_file.is_binary_or_large
        after_special = after_file and after_file.is_binary_or_large

        if before_special or after_special:
            all_diff_lines.append(f"Binary or large file changed: {rel}")
            continue

        udiff = list(
            difflib.unified_diff(
                before_lines or [],
                after_lines or [],
                fromfile=f"a/{rel}",
                tofile=f"b/{rel}",
                lineterm="",
            )
        )
        all_diff_lines.extend(udiff)
        for line in udiff:
            if line.startswith(("+++", "---", "@@")):
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
        if is_test_path(rel):
            forbidden = True
        if rel in forbidden_files:
            forbidden = True
        for pat in forbidden_patterns:
            if pat in rel or fnmatch.fnmatch(rel, pat):
                forbidden = True

    expected_files = set(expected.get("expected_files", [])) | set(expected.get("strongly_expected_files", []))
    expected_touched = any(r.startswith("repo/") and r.removeprefix("repo/") in expected_files for r in touched)

    decoys = set(failure_modes.get("decoy_files", [])) | set(expected.get("decoy_files", []))
    decoy_touched = any(r.startswith("repo/") and r.removeprefix("repo/") in decoys for r in touched)

    tests_modified = any(is_test_path(r) for r in touched)

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
