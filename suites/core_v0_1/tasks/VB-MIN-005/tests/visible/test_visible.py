import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "repo" / "src"))

from demo_warnings.deprecations import maybe_warn_deprecated


def test_old_key_warns():
    import pytest

    with pytest.warns(DeprecationWarning):
        maybe_warn_deprecated({"old_timeout": 5})
