import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from sync.scheduled import scheduled_sync_event

def test_system_actor_used_when_no_user_exists():
    assert scheduled_sync_event({"system_actor": "nightly"})["actor"] == "nightly"

def test_user_actor_still_wins_in_scheduled_replay():
    assert scheduled_sync_event({"user_id": "u9", "system_actor": "replay"})["actor"] == "u9"
