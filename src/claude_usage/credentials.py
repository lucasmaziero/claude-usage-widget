r"""Reads the OAuth token Claude Code itself stores on disk.

On Windows the file lives at %USERPROFILE%\.claude\.credentials.json, in clear
text. Re-reading it on every poll is deliberate: when Claude Code refreshes the
token, the widget picks up the new one without a restart.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from .i18n import t

CREDENTIALS_PATH = Path(os.path.expanduser("~")) / ".claude" / ".credentials.json"


class CredentialsError(Exception):
    """No usable token on disk."""


@dataclass
class Credentials:
    token: str
    expires_at: float          # epoch seconds
    subscription: str          # max | pro | ...
    tier: str

    @property
    def expired(self) -> bool:
        return self.expires_at > 0 and time.time() >= self.expires_at


def load(path: Path = CREDENTIALS_PATH) -> Credentials:
    """Parse the credentials file. Failures come back translated: they are
    rendered in the widget."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CredentialsError(t("error.no_credentials", path=path)) from None
    except (OSError, json.JSONDecodeError) as exc:
        raise CredentialsError(t("error.unreadable", path=path, reason=exc)) from None

    oauth = raw.get("claudeAiOauth") or {}
    token = oauth.get("accessToken")
    if not token:
        raise CredentialsError(t("error.no_token"))

    return Credentials(
        token=token,
        expires_at=float(oauth.get("expiresAt") or 0) / 1000.0,
        subscription=str(oauth.get("subscriptionType") or ""),
        tier=str(oauth.get("rateLimitTier") or ""),
    )
