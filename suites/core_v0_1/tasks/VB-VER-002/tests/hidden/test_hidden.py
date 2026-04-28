import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from retrying.policy import run_with_retries

def test_zero_retries_still_allows_initial_attempt():
    calls = {"n": 0}
    def op():
        calls["n"] += 1
        return "ok"
    assert run_with_retries(op, max_retries=0) == "ok"
    assert calls["n"] == 1
