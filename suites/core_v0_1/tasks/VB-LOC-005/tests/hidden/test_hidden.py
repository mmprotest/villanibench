import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from notifications.send import marketing_allowed

def test_user_opt_in_beats_disabled_account_default():
    assert marketing_allowed(True, False) is True
