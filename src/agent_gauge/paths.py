r"""Where each OS keeps the files this app reads and writes.

Claude Code itself is consistent across platforms - always `~/.claude` - so the
inputs need no per-OS logic. Only this app's own preferences do, because each
platform has a different idea of where a user-level config belongs:

    Windows   %APPDATA%\AgentGauge
    macOS     ~/Library/Application Support/AgentGauge
    Linux     $XDG_CONFIG_HOME/agent-gauge  (default ~/.config)

The Windows path is unchanged from the versions that only ran there, so an
existing install keeps its settings.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

WINDOWS = sys.platform == "win32"
MACOS = sys.platform == "darwin"
LINUX = not WINDOWS and not MACOS      # BSD included: it behaves like Linux here

APP_DIR = "AgentGauge"          # Windows and macOS convention
XDG_DIR = "agent-gauge"        # Linux convention


def os_name() -> str:
    """What to call this platform in front of the user, e.g. "Start with macOS"."""
    if WINDOWS:
        return "Windows"
    return "macOS" if MACOS else "Linux"


def home() -> Path:
    return Path(os.path.expanduser("~"))


def claude_dir() -> Path:
    """Claude Code's own directory. Same place on every platform."""
    return home() / ".claude"


def credentials_file() -> Path:
    r"""The OAuth token on disk.

    Present on Windows and Linux. On macOS this is a fallback: Claude Code puts
    the token in the login keychain there, and the file usually does not exist.
    """
    return claude_dir() / ".credentials.json"


def projects_dir() -> Path:
    """Transcripts, the only source of absolute token counts."""
    return claude_dir() / "projects"


def config_dir() -> Path:
    if WINDOWS:
        base = os.environ.get("APPDATA")
        return (Path(base) if base else home()) / APP_DIR
    if MACOS:
        return home() / "Library" / "Application Support" / APP_DIR
    base = os.environ.get("XDG_CONFIG_HOME")
    return (Path(base) if base else home() / ".config") / XDG_DIR


def config_file() -> Path:
    return config_dir() / "settings.json"
