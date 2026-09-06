"""The no-token dead ends: telling them apart, and the way out of each."""
from __future__ import annotations

import pytest

from claude_usage import credentials, i18n, paths, providers, signin
from claude_usage.panel import Panel
from claude_usage.poller import Poller
from claude_usage.settings import Settings


@pytest.fixture(autouse=True)
def _english():
    before = i18n.language()
    i18n.set_language("en")
    yield
    i18n.set_language(before)


@pytest.fixture
def no_claude_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "claude_dir", lambda: tmp_path / "absent")


@pytest.fixture
def has_claude_dir(monkeypatch, tmp_path):
    (tmp_path / ".claude").mkdir()
    monkeypatch.setattr(paths, "claude_dir", lambda: tmp_path / ".claude")


CLAUDE = providers.get("claude")


def test_no_claude_directory_means_it_was_never_installed(no_claude_dir):
    assert signin.needed(CLAUDE) == signin.INSTALL


def test_the_directory_alone_means_signed_out(has_claude_dir):
    """Deliberately not a PATH lookup: the desktop app and the IDE extensions
    write this directory and never put a `claude` binary on PATH, so a PATH test
    would tell an active user they have not installed it."""
    assert signin.needed(CLAUDE) == signin.SIGNIN


def _snapshot_without_credentials(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise credentials.CredentialsError("run `claude` once to sign in - nope.json not found")
    monkeypatch.setattr(credentials, "load", refuse)
    return Poller(120)._collect()


def test_a_missing_install_is_not_told_to_run_claude(monkeypatch, no_claude_dir):
    """"Run `claude`" is wrong advice for someone who has no Claude Code."""
    snap = _snapshot_without_credentials(monkeypatch)
    assert snap.setup == signin.INSTALL
    assert snap.error == i18n.t("error.no_claude", agent=CLAUDE.label)
    assert "`claude`" not in snap.error


def test_being_signed_out_keeps_the_original_message(monkeypatch, has_claude_dir):
    snap = _snapshot_without_credentials(monkeypatch)
    assert snap.setup == signin.SIGNIN
    assert "nope.json" in snap.error


def test_a_working_snapshot_offers_nothing(monkeypatch):
    from claude_usage import api

    monkeypatch.setattr(credentials, "load", lambda *a, **k: credentials.Credentials(
        token="t", expires_at=0, subscription="max", tier="default"))
    monkeypatch.setattr(api, "fetch_usage", lambda _token: api.Usage(h5=10, d7=5, ok=True))
    monkeypatch.setattr(api, "fetch_incidents", list)
    assert Poller(120)._collect().setup == ""


# ---------------------------------------------------------------- the panel
@pytest.mark.parametrize("state,key", [
    (signin.INSTALL, "panel.get_claude"),
    (signin.SIGNIN, "panel.how_signin"),
])
def test_the_panel_offers_the_matching_way_out(qapp, tmp_path, state, key):
    from claude_usage.poller import Snapshot

    panel = Panel(Settings(tmp_path / "settings.json"))
    panel.set_snapshot(Snapshot(error="stuck", setup=state))
    assert i18n.t(key) in panel._setup_label()
    assert not panel._setup_zone().isEmpty()


def test_a_healthy_panel_has_no_hit_zone(qapp, tmp_path):
    from claude_usage import api
    from claude_usage.poller import Snapshot

    panel = Panel(Settings(tmp_path / "settings.json"))
    panel.set_snapshot(Snapshot(usage=api.Usage(h5=10, ok=True)))
    assert panel._setup_label() == ""
    assert panel._setup_zone().isEmpty()
