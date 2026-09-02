"""Header parsing: the contract with the Anthropic API, without the network."""
from __future__ import annotations

from claude_usage import api

HEADERS_OK = {
    api.H5U: "0.71",
    api.H5R: "1788299844",
    api.H5S: "allowed",
    api.D7U: "0.34",
    api.D7R: "1788499844",
    api.D7S: "allowed",
    api.UST: "allowed_warning",
    api.URC: "five_hour",
    api.UFB: "0.5",
}


def test_parses_utilization_as_percent():
    usage = api.parse(HEADERS_OK, 200)
    assert usage.ok
    assert usage.h5 == 71.0          # headers carry a 0-1 fraction
    assert usage.d7 == 34.0
    assert usage.fallback_pct == 50.0
    assert usage.claim == "five_hour"
    assert usage.worst == 71.0


def test_reset_headers_become_epoch_ints():
    usage = api.parse(HEADERS_OK, 200)
    assert usage.h5_reset == 1788299844
    assert usage.d7_reset == 1788499844


def test_missing_optional_headers_default_to_zero():
    usage = api.parse({api.H5U: "0.1"}, 200)
    assert usage.ok
    assert usage.d7 == 0.0
    assert usage.d7_reset == 0
    assert usage.status_7d == ""


def test_garbage_values_do_not_raise():
    usage = api.parse({api.H5U: "not-a-number", api.D7U: "0.2"}, 200)
    assert usage.ok
    assert usage.h5 == 0.0
    assert usage.d7 == 20.0


def test_401_without_headers_names_the_fix():
    usage = api.parse({}, 401)
    assert not usage.ok
    assert "401" in usage.error


def test_other_failures_report_the_status_code():
    usage = api.parse({}, 500)
    assert not usage.ok
    assert "500" in usage.error


def test_rate_limited_response_still_yields_usage():
    # A 429 carries the rate-limit headers, which is exactly when they matter.
    usage = api.parse(HEADERS_OK | {api.UST: "rejected"}, 429)
    assert usage.ok
    assert usage.status_overall == "rejected"
