import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from retrying.policy import run_with_retries


def test_two_retries_allow_three_attempts_before_success():
    calls = {"n": 0}

    def op():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError(f"attempt {calls['n']}")
        return "ok"

    assert run_with_retries(op, max_retries=2) == "ok"
    assert calls["n"] == 3


def test_exhaustion_raises_last_error_after_initial_plus_retries():
    calls = {"n": 0}

    def op():
        calls["n"] += 1
        raise ValueError(f"failure {calls['n']}")

    with pytest.raises(ValueError, match="failure 3"):
        run_with_retries(op, max_retries=2)

    assert calls["n"] == 3


def test_zero_retries_propagates_initial_failure():
    calls = {"n": 0}

    def op():
        calls["n"] += 1
        raise RuntimeError("initial failure")

    with pytest.raises(RuntimeError, match="initial failure"):
        run_with_retries(op, max_retries=0)

    assert calls["n"] == 1
