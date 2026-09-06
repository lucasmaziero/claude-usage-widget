"""The macOS and Linux autostart backends, which write plain files and so can be
checked anywhere. The Windows one touches HKCU and is left to the machine that
has one - tests must not edit a developer's real Run key."""
from __future__ import annotations

import plistlib
import sys

import pytest

from agent_gauge import autostart


@pytest.fixture
def unix(monkeypatch, tmp_path):
    """Point both writers at a temp dir and take Windows out of the picture."""
    monkeypatch.setattr(autostart, "WINDOWS", False)
    monkeypatch.setattr(autostart, "PLIST", tmp_path / "LaunchAgents" / "app.plist")
    monkeypatch.setattr(autostart, "DESKTOP", tmp_path / "autostart" / "app.desktop")
    return tmp_path


def test_from_source_reinvokes_the_module(monkeypatch):
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    argv = autostart.launch_argv()
    assert argv[-2:] == ["-m", "agent_gauge"]
    assert argv[0].endswith(("python.exe", "pythonw.exe", "python", "python3"))


def test_a_frozen_build_launches_itself(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "/Applications/Claude.app/Contents/MacOS/AgentGauge")
    assert autostart.launch_argv() == ["/Applications/Claude.app/Contents/MacOS/AgentGauge"]


def test_macos_writes_a_loadable_plist(unix, monkeypatch):
    monkeypatch.setattr(autostart, "MACOS", True)
    monkeypatch.setattr(autostart, "LINUX", False)
    autostart.set_enabled(True)

    assert autostart.enabled()
    plist = plistlib.loads(autostart.PLIST.read_bytes())
    assert plist["Label"] == autostart.BUNDLE_ID
    assert plist["RunAtLoad"] is True
    assert plist["ProgramArguments"] == autostart.launch_argv()


def test_a_home_with_an_apostrophe_survives(unix, monkeypatch):
    """The reason this is plistlib and not a string template."""
    monkeypatch.setattr(autostart, "MACOS", True)
    monkeypatch.setattr(autostart, "LINUX", False)
    monkeypatch.setattr(autostart, "launch_argv", lambda: ["/Users/O'Brien & co/app"])
    autostart.set_enabled(True)
    plist = plistlib.loads(autostart.PLIST.read_bytes())
    assert plist["ProgramArguments"] == ["/Users/O'Brien & co/app"]


def test_linux_writes_a_desktop_entry(unix, monkeypatch):
    monkeypatch.setattr(autostart, "MACOS", False)
    monkeypatch.setattr(autostart, "LINUX", True)
    autostart.set_enabled(True)

    assert autostart.enabled()
    text = autostart.DESKTOP.read_text(encoding="utf-8")
    assert text.startswith("[Desktop Entry]\n")
    assert "Type=Application" in text
    assert "Terminal=false" in text
    assert any(line.startswith("Exec=") for line in text.splitlines())


def test_a_path_with_spaces_is_quoted(unix, monkeypatch):
    monkeypatch.setattr(autostart, "MACOS", False)
    monkeypatch.setattr(autostart, "LINUX", True)
    monkeypatch.setattr(autostart, "launch_argv", lambda: ["/opt/my app/run", "-m", "agent_gauge"])
    autostart.set_enabled(True)
    assert 'Exec="/opt/my app/run" -m agent_gauge' in autostart.DESKTOP.read_text(encoding="utf-8")


@pytest.mark.parametrize("os_name", ["MACOS", "LINUX"])
def test_turning_it_off_removes_the_file(unix, monkeypatch, os_name):
    monkeypatch.setattr(autostart, "MACOS", os_name == "MACOS")
    monkeypatch.setattr(autostart, "LINUX", os_name == "LINUX")
    autostart.set_enabled(True)
    assert autostart.enabled()
    autostart.set_enabled(False)
    assert not autostart.enabled()


@pytest.mark.parametrize("os_name", ["MACOS", "LINUX"])
def test_turning_off_what_was_never_on_is_quiet(unix, monkeypatch, os_name):
    monkeypatch.setattr(autostart, "MACOS", os_name == "MACOS")
    monkeypatch.setattr(autostart, "LINUX", os_name == "LINUX")
    autostart.set_enabled(False)          # must not raise
    assert not autostart.enabled()


def test_an_unwritable_location_is_swallowed(unix, monkeypatch):
    """A preference that cannot be saved is an unchecked box, not a crash."""
    monkeypatch.setattr(autostart, "MACOS", True)
    monkeypatch.setattr(autostart, "LINUX", False)
    monkeypatch.setattr(autostart, "PLIST", unix / "nope" / "x.plist")
    monkeypatch.setattr(autostart.Path, "mkdir",
                        lambda *a, **k: (_ for _ in ()).throw(PermissionError("read-only")))
    autostart.set_enabled(True)
    assert not autostart.enabled()
