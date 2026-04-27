from __future__ import annotations

import json
from pathlib import Path

from .compare import _render_report


def generate_report(comparison_dir: Path, output_path: Path) -> None:
    summary_path = comparison_dir / "comparison_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_report(summary), encoding="utf-8")
