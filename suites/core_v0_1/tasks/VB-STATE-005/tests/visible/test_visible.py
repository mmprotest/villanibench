import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from sync.manual import manual_sync_event

def test_user_actor_beats_system_actor_for_manual_sync():
    assert manual_sync_event({"user_id": "u123", "system_actor": "system"})["actor"] == "u123"
