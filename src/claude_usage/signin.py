"""What to offer when there is no token to read.

Without credentials the widget has nothing to show and, until now, nothing to
suggest either: it painted a line of red text and left the user to work out the
rest. There are two different dead ends behind that one message, and they want
different answers.

The signal is `~/.claude`, not the `claude` binary. A PATH lookup is the obvious
test and the wrong one: Claude Code is also used through the desktop app and the
IDE extensions, which never put a CLI on PATH, so plenty of active users would
be told they have not installed it. The directory is written by all of them.

Nothing here installs anything. Piping an install script into a shell on the
user's behalf is not a thing a monitoring widget should do, and the script is
not ours to keep working; a link to the page that documents both installing and
signing in costs one click and cannot rot into running the wrong command.
"""
from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from . import paths

# docs.claude.com/en/docs/claude-code/setup redirects here; this is the target.
# The page covers installation and the sign-in step, which is exactly the span
# between the two states below.
HELP_URL = "https://code.claude.com/docs/en/setup"

INSTALL = "install"      # no sign of Claude Code on this machine
SIGNIN = "signin"        # it has been used here, but there is no usable token


def needed() -> str:
    """Which dead end the user is at, as INSTALL or SIGNIN."""
    return SIGNIN if paths.claude_dir().exists() else INSTALL


def open_help() -> None:
    """Hand the setup page to the user's browser."""
    QDesktopServices.openUrl(QUrl(HELP_URL))
