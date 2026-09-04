r"""Reads the OAuth token Claude Code itself stores, wherever it stores it.

Two shapes, same JSON inside:

    Windows   %USERPROFILE%\.claude\.credentials.json, clear text
    Linux     ~/.claude/.credentials.json, clear text
    macOS     the login keychain, under the service "Claude Code-credentials"

Re-reading on every poll is deliberate: when Claude Code refreshes the token,
the widget picks up the new one without a restart. On macOS that means one
`security` call per cycle, which is a few milliseconds and, after the user
allows it once, silent.
"""
from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .i18n import t
from .paths import MACOS, credentials_file

KEYCHAIN_SERVICE = "Claude Code-credentials"
KEYCHAIN_TIMEOUT = 10       # the first call can sit on an authorization dialog

CREDENTIALS_PATH = credentials_file()


class CredentialsError(Exception):
    """No usable token where Claude Code would have left one."""


@dataclass
class Credentials:
    token: str
    expires_at: float          # epoch seconds
    subscription: str          # max | pro | ...
    tier: str

    @property
    def expired(self) -> bool:
        return self.expires_at > 0 and time.time() >= self.expires_at


def read_keychain() -> str | None:
    """The credentials blob from the macOS login keychain, or None.

    None covers every way this can come up empty - not signed in, the item
    renamed, the user denying access - because the caller falls back to the
    file either way and reports one error for both.
    """
    try:
        proc = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True, text=True, timeout=KEYCHAIN_TIMEOUT, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def _read_raw(path: Path) -> str:
    """The credentials JSON as text, from the most authoritative source first."""
    if MACOS:
        blob = read_keychain()
        if blob:
            return blob
        if not path.exists():
            raise CredentialsError(t("error.no_keychain"))
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise CredentialsError(t("error.no_credentials", path=path)) from None
    except OSError as exc:
        raise CredentialsError(t("error.unreadable", path=path, reason=exc)) from None


def load(path: Path | None = None) -> Credentials:
    """Parse the credentials. Failures come back translated: they are rendered
    in the widget."""
    source = path if path is not None else credentials_file()
    try:
        raw = json.loads(_read_raw(source))
    except json.JSONDecodeError as exc:
        raise CredentialsError(t("error.unreadable", path=source, reason=exc)) from None

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
