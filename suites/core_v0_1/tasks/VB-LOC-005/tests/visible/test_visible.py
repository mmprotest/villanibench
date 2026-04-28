import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from notifications.send import marketing_allowed

def test_user_opt_out_beats_enabled_account_default():
    assert marketing_allowed(False, True) is False
