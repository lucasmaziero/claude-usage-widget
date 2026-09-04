"""Is there a newer build than this one?

The widget installs itself and never updates itself: there is no updater, no
background check, and nothing here runs unless the user asks. All this does is
read the latest tag GitHub publishes and compare it with the version this
build was cut from.

Kept apart from api.py on purpose. That module talks to Anthropic with Claude
Code's own User-Agent because it is reading Claude Code's rate limits; this one
talks to GitHub as itself.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from . import __version__

REPO = "lucasmaziero/claude-usage-widget"
LATEST_ENDPOINT = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{REPO}/releases/latest"
USER_AGENT = f"claude-usage-widget/{__version__}"
TIMEOUT = 10


def parse(text: str) -> tuple[int, ...]:
    """"v1.2.0" -> (1, 2, 0).

    Anything after a dash or a plus is a pre-release or build marker and is
    dropped; anything that will not parse yields an empty tuple, which every
    comparison below treats as "do not claim anything".
    """
    core = text.strip().lstrip("vV").split("-")[0].split("+")[0]
    try:
        return tuple(int(part) for part in core.split("."))
    except ValueError:
        return ()


def is_newer(latest: str, current: str = __version__) -> bool:
    """Whether `latest` is ahead of `current`, padding the shorter one with
    zeros so 1.2 and 1.2.0 compare equal.

    False whenever either side is unreadable. Telling a user an update exists
    when it does not is worse than staying quiet.
    """
    new, have = parse(latest), parse(current)
    if not new or not have:
        return False
    width = max(len(new), len(have))
    return new + (0,) * (width - len(new)) > have + (0,) * (width - len(have))


def fetch_latest() -> str:
    """The newest published tag, or "" if GitHub could not be reached.

    An empty string is not "you are up to date" - the caller has to say the
    check failed, not that it passed.
    """
    request = urllib.request.Request(
        LATEST_ENDPOINT,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return ""
    return str(data.get("tag_name") or "")
