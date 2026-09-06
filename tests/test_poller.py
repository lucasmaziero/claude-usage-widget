"""The collection loop: the baseline that survives a restart, the pruning that
keeps it honest, and the backoff that stops paying for readings nobody wants."""
from __future__ import annotations

import json
import time

import pytest

from agent_gauge import api, credentials, poller, tokens
from agent_gauge.poller import Poller


@pytest.fixture(autouse=True)
def history_file(monkeypatch, tmp_path):
    """Never the developer's real one."""
    path = tmp_path / "history.json"
    monkeypatch.setattr(poller, "HISTORY_FILE", path)
    return path


def _signed_in(monkeypatch):
    monkeypatch.setattr(credentials, "load", lambda *a, **k: credentials.Credentials(
        token="t", expires_at=0, subscription="max", tier="default"))
    monkeypatch.setattr(api, "fetch_incidents", list)


def _usage(h5: float, reset_in: float = 3 * 3600) -> api.Usage:
    return api.Usage(h5=h5, d7=5, h5_reset=int(time.time() + reset_in), ok=True)


# ------------------------------------------------------------------ history
def test_the_baseline_survives_a_restart(history_file, monkeypatch):
    """An app that starts with the session would otherwise have no projection
    for the first few minutes of every day."""
    _signed_in(monkeypatch)
    monkeypatch.setattr(api, "fetch_usage", lambda _t: _usage(20))
    first = Poller(120)
    first._collect()
    assert history_file.exists()

    second = Poller(120)
    assert len(second.history) == 1
    assert second.history[0][1] == 20


def test_samples_older_than_a_window_are_dropped_on_load(history_file):
    stale = time.time() - tokens.WINDOW_SECONDS - 60
    fresh = time.time() - 60
    history_file.write_text(json.dumps([[stale, 90.0], [fresh, 12.0]]), encoding="utf-8")

    loaded = Poller(120)
    assert [pct for _when, pct in loaded.history] == [12.0]


def test_a_malformed_row_does_not_lose_the_rest(history_file):
    fresh = time.time() - 60
    history_file.write_text(
        json.dumps([[fresh, 10.0], "junk", [fresh, None], [fresh, 11.0]]), encoding="utf-8")
    assert [pct for _w, pct in Poller(120).history] == [10.0, 11.0]


def test_an_unreadable_file_is_simply_no_baseline(history_file):
    history_file.write_text("{not json", encoding="utf-8")
    assert len(Poller(120).history) == 0


def test_a_missing_file_is_not_an_error(history_file):
    assert not history_file.exists()
    assert len(Poller(120).history) == 0


def test_samples_from_before_this_window_are_pruned(monkeypatch, history_file):
    """The bug this fixes: after a reset the old high samples stayed, burn_rate
    saw the percentage fall, and returned zero for hours."""
    _signed_in(monkeypatch)
    p = Poller(120)
    now = time.time()
    reset_in = 3 * 3600
    window_start = now + reset_in - tokens.WINDOW_SECONDS
    p.history.append((window_start - 600, 95.0))          # the window before this one
    p.history.append((window_start - 300, 97.0))

    monkeypatch.setattr(api, "fetch_usage", lambda _t: _usage(4, reset_in))
    p._collect()

    assert [pct for _w, pct in p.history] == [4.0]


def test_burn_rate_recovers_after_a_reset(monkeypatch, history_file):
    _signed_in(monkeypatch)
    p = Poller(120)
    now = time.time()
    reset_in = 3 * 3600
    start = now + reset_in - tokens.WINDOW_SECONDS
    p.history.append((start - 100, 96.0))                 # stale, from the old window

    monkeypatch.setattr(api, "fetch_usage", lambda _t: _usage(5, reset_in))
    p._collect()
    p.history.append((time.time() + 1800, 15.0))          # half an hour later

    assert p.burn_rate() > 0


# -------------------------------------------------------------- credentials
def test_an_expired_token_skips_the_request(monkeypatch, history_file):
    """The timestamp is the one Claude Code refreshes against, so the request
    would come back 401. Sending it anyway spends a token to learn nothing."""
    monkeypatch.setattr(credentials, "load", lambda *a, **k: credentials.Credentials(
        token="t", expires_at=time.time() - 1, subscription="max", tier="default"))

    def must_not_run(_token):
        raise AssertionError("the probe was sent for a token known to be expired")
    monkeypatch.setattr(api, "fetch_usage", must_not_run)

    snap = Poller(120)._collect()
    assert not snap.ok


def test_an_expired_token_is_a_resting_state_not_a_fault(monkeypatch, history_file):
    """Eight hours without Claude Code is the app's normal overnight condition.
    Reporting it as an error taught the user to ignore the colour that means
    something is actually wrong."""
    monkeypatch.setattr(credentials, "load", lambda *a, **k: credentials.Credentials(
        token="t", expires_at=time.time() - 1, subscription="max", tier="default"))
    monkeypatch.setattr(api, "fetch_usage", lambda _t: api.Usage(ok=True))

    poll = Poller(120)
    snap = poll._collect()
    assert snap.waiting
    assert snap.setup == ""              # nothing to click that would help
    assert poll._watching                # so the file, not the clock, ends the wait


def test_a_real_failure_is_still_a_failure(monkeypatch, history_file):
    _signed_in(monkeypatch)
    monkeypatch.setattr(api, "fetch_usage",
                        lambda _t: api.Usage(ok=False, code=401, error="refused"))
    poll = Poller(120)
    snap = poll._collect()
    assert not snap.waiting
    assert not poll._watching


def test_the_wait_ends_when_claude_code_writes(monkeypatch, history_file):
    """The point of watching: recovery in seconds rather than up to a full
    interval after the token is renewed."""
    poll = Poller(120)
    poll._watching = True
    monkeypatch.setattr(Poller, "CREDS_POLL", 0.01)
    mtimes = iter([100.0, 100.0, 200.0])
    monkeypatch.setattr(poll, "_creds_mtime", lambda: next(mtimes))

    started = time.monotonic()
    poll._sleep(30)
    assert time.monotonic() - started < 1.0


def test_a_healthy_cycle_never_stats_the_file(monkeypatch, history_file):
    poll = Poller(120)
    poll._watching = False
    stats = []
    monkeypatch.setattr(poll, "_creds_mtime", lambda: stats.append(1) or 0.0)
    poll._wake.set()
    poll._sleep(30)
    assert not stats


# ----------------------------------------------------------------- backoff
@pytest.mark.parametrize("idle,expected", [
    (0, 120), (1, 120), (2, 120),          # still inside IDLE_AFTER
    (3, 240), (4, 480), (5, 480), (99, 480),
])
def test_the_wait_stretches_only_while_nothing_moves(idle, expected, history_file):
    p = Poller(120)
    p._idle = idle
    assert p._effective_interval() == expected


def test_an_unchanged_reading_counts_as_idle(monkeypatch, history_file):
    _signed_in(monkeypatch)
    monkeypatch.setattr(api, "fetch_usage", lambda _t: _usage(30))
    p = Poller(120)
    for _ in range(3):
        p._collect()
    assert p._idle == 2                     # the first reading has nothing to compare to
    assert p._effective_interval() == 120

    p._collect()
    assert p._effective_interval() == 240


def test_movement_puts_the_cadence_straight_back(monkeypatch, history_file):
    _signed_in(monkeypatch)
    p = Poller(120)
    p._idle, p._last_h5 = 9, 30.0
    monkeypatch.setattr(api, "fetch_usage", lambda _t: _usage(31))
    p._collect()
    assert p._idle == 0
    assert p._effective_interval() == 120


def test_a_failure_does_not_slow_the_recovery(monkeypatch, history_file):
    _signed_in(monkeypatch)
    p = Poller(120)
    p._idle = 9
    monkeypatch.setattr(api, "fetch_usage",
                        lambda _t: api.Usage(ok=False, error="network"))
    p._collect()
    assert p._effective_interval() == 120


def test_asking_by_hand_asks_now(history_file):
    p = Poller(120)
    p._idle = 9
    p.refresh()
    assert p._effective_interval() == 120
