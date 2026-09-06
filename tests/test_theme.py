"""Palette ramp and formatters."""
from __future__ import annotations

import pytest

from agent_gauge import api, i18n, theme


@pytest.fixture(autouse=True)
def _english():
    """Pinned, not inherited from the machine.

    These assertions used to read whatever language Windows was set to, so they
    passed on a pt-BR desktop and failed on an English CI runner. Coverage of
    the other language lives in test_i18n.py.
    """
    before = i18n.language()
    i18n.set_language("en")
    yield
    i18n.set_language(before)


def test_ramp_ends_match_the_palette():
    assert theme.grad_color(0).name() == theme.OK.name()
    assert theme.grad_color(50).name() == theme.WARN.name()
    assert theme.grad_color(100).name() == theme.BAD.name()


def test_ramp_is_clamped_outside_0_100():
    assert theme.grad_color(-20).name() == theme.OK.name()
    assert theme.grad_color(180).name() == theme.BAD.name()


def test_countdown_units():
    now = 1_000_000
    assert theme.fmt_countdown(now + 2 * 86400 + 3600, now) == "2d01h"
    assert theme.fmt_countdown(now + 2 * 3600 + 13 * 60, now) == "2h13"
    assert theme.fmt_countdown(now + 47 * 60, now) == "47min"
    assert theme.fmt_countdown(now + 38, now) == "38s"
    assert theme.fmt_countdown(now - 5, now) == "now"
    assert theme.fmt_countdown(0, now) == "--"


def test_token_shortening():
    assert theme.fmt_tokens(512) == "512"
    assert theme.fmt_tokens(24_000) == "24k"
    assert theme.fmt_tokens(6_029_281) == "6.0M"


def test_status_chip_follows_header_then_percentage():
    assert theme.status_label(api.Usage(ok=True, status_overall="allowed"))[0] == "OK"
    assert theme.status_label(api.Usage(ok=True, status_overall="allowed_warning"))[0] == "WARNING"
    assert theme.status_label(api.Usage(ok=True, status_overall="rejected"))[0] == "BLOCKED"
    assert theme.status_label(api.Usage(ok=True, h5=95, status_overall="allowed"))[0] == "WARNING"
    assert theme.status_label(api.Usage(ok=False))[0] == "NO DATA"


def test_window_elapsed_is_a_fraction():
    now = 1_000_000
    span = 5 * 3600
    assert theme.window_elapsed(now + span, span, now) == 0.0
    assert theme.window_elapsed(now + span / 2, span, now) == 0.5
    assert theme.window_elapsed(0, span, now) == 0.0        # no header yet
