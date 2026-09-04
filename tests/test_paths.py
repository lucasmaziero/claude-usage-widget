"""Per-OS locations. The flags are module globals so the branches are reachable
from any host: each test pins the platform it is asking about."""
from __future__ import annotations

from pathlib import Path

import pytest

from claude_usage import paths


@pytest.fixture
def fake_home(monkeypatch, tmp_path) -> Path:
    monkeypatch.setattr(paths, "home", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def on(monkeypatch):
    """Pin the platform: on("darwin") makes MACOS true and the others false."""
    def pin(name: str) -> None:
        for flag, value in (("WINDOWS", "win32"), ("MACOS", "darwin"), ("LINUX", "linux")):
            monkeypatch.setattr(paths, flag, name == value)
    return pin


def test_claude_inputs_are_the_same_everywhere(fake_home, on):
    """Claude Code itself uses ~/.claude on all three, so nothing to branch on."""
    for name in ("win32", "darwin", "linux"):
        on(name)
        assert paths.credentials_file() == fake_home / ".claude" / ".credentials.json"
        assert paths.projects_dir() == fake_home / ".claude" / "projects"


def test_windows_config_follows_appdata(fake_home, on, monkeypatch):
    on("win32")
    monkeypatch.setenv("APPDATA", str(fake_home / "Roaming"))
    assert paths.config_dir() == fake_home / "Roaming" / "ClaudeUsageWidget"


def test_windows_config_falls_back_to_home(fake_home, on, monkeypatch):
    on("win32")
    monkeypatch.delenv("APPDATA", raising=False)
    assert paths.config_dir() == fake_home / "ClaudeUsageWidget"


def test_macos_config_is_application_support(fake_home, on):
    on("darwin")
    assert paths.config_dir() == (fake_home / "Library" / "Application Support"
                                  / "ClaudeUsageWidget")


def test_linux_config_honours_xdg(fake_home, on, monkeypatch):
    on("linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(fake_home / "xdg"))
    assert paths.config_dir() == fake_home / "xdg" / "claude-usage-widget"


def test_linux_config_defaults_to_dot_config(fake_home, on, monkeypatch):
    on("linux")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    assert paths.config_dir() == fake_home / ".config" / "claude-usage-widget"


def test_exactly_one_platform_is_live():
    """The real flags, not the pinned ones: LINUX is the catch-all."""
    assert sum((paths.WINDOWS, paths.MACOS, paths.LINUX)) == 1
