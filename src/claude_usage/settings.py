r"""User preferences, stored in %APPDATA%\ClaudeUsageWidget\settings.json."""
from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("APPDATA") or Path.home()) / "ClaudeUsageWidget"
CONFIG_FILE = CONFIG_DIR / "settings.json"

MIN_POLL = 30
MAX_POLL = 900

DEFAULTS: dict = {
    "pos_x": None,          # None: park in the bottom-right corner
    "pos_y": None,
    "poll_sec": 120,        # fresh enough to act on, cheap enough to ignore
    "opacity": 0.96,
    "locked": False,        # ignore dragging
    "widget_visible": True,
    "compact": False,       # ring only, no text rows
    "language": "auto",     # auto follows Windows; "en" or "pt_BR" pin it
}


class Settings(dict):
    """Dict of preferences that loads on construction and saves on demand."""

    def __init__(self, path: Path = CONFIG_FILE) -> None:
        super().__init__(DEFAULTS)
        self.path = path
        self.load()

    def load(self) -> None:
        """Merge stored values over the defaults; unknown keys are dropped."""
        try:
            stored = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for key in DEFAULTS:
            if key in stored:
                self[key] = stored[key]
        self["poll_sec"] = min(max(int(self["poll_sec"]), MIN_POLL), MAX_POLL)

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(dict(self), indent=2), encoding="utf-8")
        except OSError:
            pass  # an unsaved preference must never take the app down
