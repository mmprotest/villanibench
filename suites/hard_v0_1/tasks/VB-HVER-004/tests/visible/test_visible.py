import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from retry.policy import should_retry


def test_provider_prefixed_timeout_is_retried():
    assert should_retry("stripe.timeout", attempt=1) is True
