import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from retry.policy import should_retry


def test_permanent_errors_are_not_retried_and_attempt_limit_holds():
    assert should_retry("validation", attempt=1) is False
    assert should_retry("provider.rate_limit", attempt=3) is False
