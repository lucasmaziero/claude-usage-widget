"""Shared fixtures.

Qt needs a platform plugin even with nothing to show; `offscreen` keeps the
render tests headless and stops windows from flashing on a developer machine.
The variable must be set before the first Qt import.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QFont, QFontInfo
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """One QApplication for the whole session; Qt forbids a second one."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def real_fonts(qapp) -> None:
    """Skip unless Qt resolved exactly the font the layout was measured against.

    Two ways to end up with different metrics: the offscreen plugin ships a stub
    font database whose fallback runs about 1.8x wider, and Windows Server has
    Segoe UI but not the Variable Display cut that ships with Windows 11. A name
    check passes the second case and then measures the wrong font, so this asks
    for an exact match.

    Run the whole suite against the real thing with:

        $env:QT_QPA_PLATFORM = "windows"; uv run pytest
    """
    wanted = QFont("Segoe UI Variable Display")
    if not wanted.exactMatch():
        got = QFontInfo(wanted).family() or "no font database"
        pytest.skip(f"needs Segoe UI Variable Display, Qt resolved {got!r}")
