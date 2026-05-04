import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from retrying.policy import run_with_retries


def test_one_retry_allows_two_attempts():
    calls = {"n": 0}

    def op():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("try again")
        return "ok"

    assert run_with_retries(op, max_retries=1) == "ok"
    assert calls["n"] == 2


def test_zero_retries_allows_one_successful_attempt():
    calls = {"n": 0}

    def op():
        calls["n"] += 1
        return "ok"

    assert run_with_retries(op, max_retries=0) == "ok"
    assert calls["n"] == 1
