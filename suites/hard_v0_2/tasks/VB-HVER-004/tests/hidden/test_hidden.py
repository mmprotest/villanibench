import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "repo" / "src"))

from retry.policy import PERMANENT, TRANSIENT, should_retry


def test_all_known_transient_codes_work_plain_and_provider_prefixed():
    for code in TRANSIENT:
        assert should_retry(code, attempt=1) is True
        assert should_retry(f"provider_a.{code}", attempt=1) is True
        assert should_retry(f"nested.provider.{code}", attempt=1) is True


def test_permanent_codes_are_never_retried_plain_or_provider_prefixed():
    for code in PERMANENT:
        assert should_retry(code, attempt=1) is False
        assert should_retry(f"stripe.{code}", attempt=1) is False
        assert should_retry(f"nested.provider.{code}", attempt=1) is False


def test_unknown_codes_are_not_retried_even_when_prefixed():
    assert should_retry("temporary_validation", attempt=1) is False
    assert should_retry("stripe.quota_exhausted", attempt=1) is False
    assert should_retry("provider.timeout_extra", attempt=1) is False


def test_attempt_limit_applies_to_plain_and_prefixed_transients():
    assert should_retry("timeout", attempt=2, max_attempts=3) is True
    assert should_retry("timeout", attempt=3, max_attempts=3) is False
    assert should_retry("stripe.rate_limit", attempt=2, max_attempts=3) is True
    assert should_retry("stripe.rate_limit", attempt=3, max_attempts=3) is False


def test_error_prefix_alone_is_not_enough_to_retry():
    assert should_retry("timeout.validation", attempt=1) is False
    assert should_retry("rate_limit.permission", attempt=1) is False
