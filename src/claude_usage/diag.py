"""A short record of failed cycles, for the bugs that only happen at 3am.

A widget that goes red while nobody is watching leaves nothing behind: the
message is on screen until the next cycle overwrites it, and by the time anyone
looks the app has recovered and the evidence is gone. This keeps the last few
hundred failures on disk with the context that tells them apart.

What it deliberately does not write: the access token, the refresh token, or
anything derived from either. Only whether a token had expired, and by how
long - which is the question, and is answerable from a timestamp.

Successes are not logged. The file should stay empty on a healthy machine, so
its size is itself a signal.
"""
from __future__ import annotations

import time
from pathlib import Path

from . import paths

LOG_FILE = paths.config_dir() / "errors.log"
MAX_LINES = 200          # a few weeks of an occasional blip, a day of a bad one


def _format(kind: str, fields: dict) -> str:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    parts = " ".join(f"{key}={value}" for key, value in fields.items()
                     if value is not None and value != "")
    return f"{stamp} {kind} {parts}".rstrip()


def record(kind: str, **fields) -> None:
    """Append one failure. Never raises: diagnostics must not be the thing that
    takes the app down."""
    try:
        line = _format(kind, fields)
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        previous = []
        if LOG_FILE.exists():
            previous = LOG_FILE.read_text(encoding="utf-8").splitlines()
        kept = [*previous, line][-MAX_LINES:]
        LOG_FILE.write_text("\n".join(kept) + "\n", encoding="utf-8")
    except OSError:
        pass


def credentials_context() -> dict:
    """When the token expires and when Claude Code last rewrote the file.

    Both are the crux of the question this exists to answer: whether a failure
    is a token that genuinely ran out, or one the server rejected while the
    file still called it valid.
    """
    context: dict = {}
    try:
        stat = paths.credentials_file().stat()
    except OSError:
        return {"creds": "missing"}
    context["creds_age_min"] = f"{(time.time() - stat.st_mtime) / 60:.0f}"

    try:
        import json

        oauth = json.loads(
            paths.credentials_file().read_text(encoding="utf-8")).get("claudeAiOauth") or {}
        expires_at = float(oauth.get("expiresAt") or 0) / 1000.0
    except (OSError, ValueError, AttributeError):
        return context

    if expires_at:
        left = expires_at - time.time()
        context["expires_in_min"] = f"{left / 60:.0f}"
        context["past_expiry"] = "yes" if left <= 0 else "no"
    return context


def path() -> Path:
    return LOG_FILE
