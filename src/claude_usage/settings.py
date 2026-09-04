"""User preferences, in the per-user config directory of whatever OS is running.

See `paths.config_dir` for the three locations.
"""
from __future__ import annotations

import json
from pathlib import Path

from .paths import config_dir, config_file

CONFIG_DIR = config_dir()
CONFIG_FILE = config_file()

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
    "language": "auto",     # auto follows the system; "en" or "pt_BR" pin it
    "alert_at": 80,         # notify once per window at this percent; 0 is off
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
