import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'repo' / 'src'))

from notifications.send import should_send_marketing_email

def test_user_opt_in_beats_account_default_false():
    assert should_send_marketing_email(True, False, False) is True
