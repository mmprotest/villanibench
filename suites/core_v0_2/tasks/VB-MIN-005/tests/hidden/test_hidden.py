import warnings
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "repo" / "src"))

from demo_warnings.deprecations import maybe_warn_deprecated


def test_new_key_does_not_warn():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        maybe_warn_deprecated({"new_timeout": 5})
    assert not caught
