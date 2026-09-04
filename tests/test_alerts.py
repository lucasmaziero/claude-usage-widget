"""When the app is allowed to speak first.

A display only works if you look at it. The alert is the one place this app
interrupts, so the rule for when it may has to be exact: once per window, on
the first reading that crosses the line, and never on data it does not trust.
"""
from __future__ import annotations

import time

from claude_usage import api
from claude_usage.app import alert_due
from claude_usage.poller import Snapshot

RESET = int(time.time() + 3600)
NEVER = -1                      # nothing announced yet


def snap(h5: float, reset: int = RESET, ok: bool = True, error: str = "") -> Snapshot:
    return Snapshot(usage=api.Usage(h5=h5, h5_reset=reset, ok=ok), error=error)


def test_crossing_the_threshold_alerts():
    assert alert_due(snap(80), 80, NEVER)
    assert alert_due(snap(95), 80, NEVER)


def test_below_the_threshold_is_silent():
    assert not alert_due(snap(79.9), 80, NEVER)


def test_zero_means_off():
    """Off has to be off even at 100%."""
    assert not alert_due(snap(100), 0, NEVER)


def test_only_once_per_window():
    already = RESET
    assert not alert_due(snap(85), 80, already)
    assert not alert_due(snap(99), 80, already)


def test_a_new_window_rearms_it():
    assert alert_due(snap(85, reset=RESET + 18000), 80, RESET)


def test_never_on_a_failed_reading():
    """A stale or errored snapshot can carry any number; interrupting on one
    would be an alert about nothing."""
    assert not alert_due(snap(99, ok=False), 80, NEVER)
    assert not alert_due(snap(99, error="network"), 80, NEVER)


def test_starting_up_above_the_line_still_alerts():
    """A fresh process has announced nothing, which is exactly when someone who
    left it running through lunch wants to hear about it."""
    assert alert_due(snap(88), 80, NEVER)


def test_a_lowered_threshold_can_fire_immediately():
    """_alerted_for is reset when the setting changes, so this is the state the
    app is in right after the user picks a smaller number."""
    assert alert_due(snap(60), 50, NEVER)
