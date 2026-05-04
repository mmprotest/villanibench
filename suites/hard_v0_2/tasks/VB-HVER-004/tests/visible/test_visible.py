import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "repo" / "src"))

from retry.policy import should_retry


def test_provider_prefixed_timeout_is_retried_before_attempt_limit():
    assert should_retry("stripe.timeout", attempt=1) is True


def test_plain_transient_behavior_is_preserved():
    assert should_retry("rate_limit", attempt=1) is True
