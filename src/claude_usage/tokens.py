"""Real token counts for the current 5h window, read from local transcripts.

The unified-* headers only report a percentage; the absolute numbers exist only
in Claude Code's transcripts (~/.claude/projects/**/*.jsonl). The widget runs on
the same machine, so it reads them straight off the disk.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .paths import projects_dir

PROJECTS = projects_dir()
WINDOW_SECONDS = 5 * 3600


@dataclass
class TokenTotals:
    input: int = 0
    output: int = 0
    cache_read: int = 0
    sessions: int = 0

    @property
    def total(self) -> int:
        return self.input + self.output


def _parse_ts(ts: str) -> float:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return 0.0


def collect(start: float, projects: Path = PROJECTS) -> TokenTotals:
    """Sum `usage` across messages stamped at or after `start`, deduped by id.

    Transcripts repeat a message when a session is resumed, hence the dedup.
    """
    totals = TokenTotals()
    seen: set[str] = set()
    files: set[Path] = set()

    for path in projects.glob("*/*.jsonl"):
        try:
            if path.stat().st_mtime < start - 60:
                continue  # untouched since before the window
            with path.open("r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if '"usage"' not in line:
                        continue  # cheap reject before parsing JSON
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    msg = rec.get("message") or {}
                    usage = msg.get("usage")
                    if not usage or _parse_ts(rec.get("timestamp", "")) < start:
                        continue
                    key = msg.get("id") or rec.get("uuid")
                    if key:
                        if key in seen:
                            continue
                        seen.add(key)
                    totals.input += (usage.get("input_tokens") or 0) + (
                        usage.get("cache_creation_input_tokens") or 0
                    )
                    totals.output += usage.get("output_tokens") or 0
                    totals.cache_read += usage.get("cache_read_input_tokens") or 0
                    files.add(path)
        except OSError:
            continue

    totals.sessions = len(files)
    return totals


def window_start(h5_reset: int, now: float | None = None) -> float:
    """Start of the 5h window: reset minus 5h.

    Falls back to "the last 5 hours" when the reset header is missing or stale,
    which happens before the first successful fetch.
    """
    now = time.time() if now is None else now
    if h5_reset > now - 86400:
        return h5_reset - WINDOW_SECONDS
    return now - WINDOW_SECONDS
