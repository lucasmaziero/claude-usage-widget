"""Claude Code, which is what this app was built around.

Nothing here is new. The modules it delegates to are the ones that have always
done this work; this only states them as one provider so a second can exist
beside it.
"""
from __future__ import annotations

from pathlib import Path

from .. import api, credentials, paths, tokens
from ..credentials import Credentials
from .base import Provider


class Claude(Provider):
    key = "claude"
    label = "Claude Code"
    short = "Claude"
    help_url = "https://code.claude.com/docs/en/setup"
    status_host = "status.claude.com"

    def home(self) -> Path:
        return paths.claude_dir()

    def credentials(self) -> Credentials:
        return credentials.load(agent=self.label)

    def fetch(self, creds: Credentials) -> api.Usage:
        return api.fetch_usage(creds.token)

    def incidents(self) -> list[str]:
        return api.fetch_incidents()

    def totals(self, since: float) -> tokens.TokenTotals:
        return tokens.collect(since)
