import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from sla.api import breached


def test_paused_time_is_subtracted_before_comparing_to_limit():
    assert breached(85, 30, 60) is False


def test_ticket_breaches_when_active_minutes_exceed_limit():
    assert breached(95, 20, 60) is True


def test_unpaused_ticket_still_breaches_normally():
    assert breached(61, 0, 60) is True


def test_exact_limit_is_not_a_breach_after_pause_adjustment():
    assert breached(90, 30, 60) is False
