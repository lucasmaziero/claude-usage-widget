r"""Start with the session, one backend per platform.

Three unrelated mechanisms behind one on/off switch:

    Windows   HKCU\...\CurrentVersion\Run, a registry value
    macOS     a LaunchAgent plist in ~/Library/LaunchAgents
    Linux     a .desktop file in ~/.config/autostart (freedesktop spec)

All three take effect at the next login, and all three are per user: none of
them needs admin, and none of them touches anything outside $HOME.

Every failure is swallowed. A preference that cannot be written is a checkbox
that stays unchecked, never an app that dies on a menu click.
"""
from __future__ import annotations

import contextlib
import plistlib
import sys
from pathlib import Path

from .paths import LINUX, MACOS, WINDOWS, home

APP_ID = "AgentGauge"
APP_NAME = "Agent Gauge"
BUNDLE_ID = "com.lucasmaziero.agent-gauge"

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
PLIST = home() / "Library" / "LaunchAgents" / f"{BUNDLE_ID}.plist"
DESKTOP = home() / ".config" / "autostart" / "agent-gauge.desktop"


def launch_argv() -> list[str]:
    """How to start this app again from scratch.

    A frozen build launches its own executable. From source it is the
    interpreter plus `-m agent_gauge`, preferring pythonw.exe on Windows so no
    console flashes at logon.
    """
    if getattr(sys, "frozen", False):
        return [sys.executable]
    exe = Path(sys.executable)
    if WINDOWS:
        pythonw = exe.with_name("pythonw.exe")
        if pythonw.exists():
            exe = pythonw
    return [str(exe), "-m", "agent_gauge"]


# ---------------------------------------------------------------- Windows
def _win_enabled() -> bool:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_ID)
        return True
    except OSError:
        return False


def _win_set(enabled: bool) -> None:
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if not enabled:
            with contextlib.suppress(FileNotFoundError):
                winreg.DeleteValue(key, APP_ID)
            return
        argv = launch_argv()
        cmd = " ".join(f'"{arg}"' if " " in arg else arg for arg in argv)
        winreg.SetValueEx(key, APP_ID, 0, winreg.REG_SZ, cmd)


# ------------------------------------------------------------------ macOS
def _mac_set(enabled: bool) -> None:
    if not enabled:
        PLIST.unlink(missing_ok=True)
        return
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    # plistlib rather than a template: the executable path is user data, and an
    # apostrophe in a home directory name would otherwise break the XML.
    with PLIST.open("wb") as fh:
        plistlib.dump({
            "Label": BUNDLE_ID,
            "ProgramArguments": launch_argv(),
            "RunAtLoad": True,
            # A tray app that exits is a user quitting it, not a crash to undo.
            "KeepAlive": False,
            "ProcessType": "Interactive",
        }, fh)


# ------------------------------------------------------------------ Linux
def _linux_set(enabled: bool) -> None:
    if not enabled:
        DESKTOP.unlink(missing_ok=True)
        return
    DESKTOP.parent.mkdir(parents=True, exist_ok=True)
    exec_line = " ".join(f'"{arg}"' if " " in arg else arg for arg in launch_argv())
    DESKTOP.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        f"Exec={exec_line}\n"
        "Icon=agent-gauge\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n",
        encoding="utf-8",
    )


# ----------------------------------------------------------------- public
def enabled() -> bool:
    try:
        if WINDOWS:
            return _win_enabled()
        return (PLIST if MACOS else DESKTOP).exists()
    except OSError:
        return False


def set_enabled(on: bool) -> None:
    try:
        if WINDOWS:
            _win_set(on)
        elif MACOS:
            _mac_set(on)
        elif LINUX:
            _linux_set(on)
    except OSError:
        pass
