"""The providers the widget can watch, and which one it is watching."""
from __future__ import annotations

from .base import Provider
from .claude import Claude
from .codex import Codex

# Order is the order the menu offers them.
ALL: tuple[Provider, ...] = (Claude(), Codex())
BY_KEY = {provider.key: provider for provider in ALL}
DEFAULT = ALL[0].key


def get(key: str) -> Provider:
    """The named provider, falling back to the default rather than raising: a
    settings file naming a provider this build does not have must not stop the
    app from starting."""
    return BY_KEY.get(key, BY_KEY[DEFAULT])


__all__ = ["ALL", "BY_KEY", "DEFAULT", "Claude", "Codex", "Provider", "get"]
