import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'repo' / 'src'))

from notifications.send import should_send_marketing_email

def test_account_default_used_when_user_pref_missing():
    assert should_send_marketing_email(None, False, True) is False
