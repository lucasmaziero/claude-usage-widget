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
    """Skip unless Qt resolved the actual UI font.

    The offscreen plugin ships a stub font database whose fallback runs about
    1.8x wider than Segoe UI, so any assertion in pixels is meaningless there.
    Run the whole suite against the real thing with:

        $env:QT_QPA_PLATFORM = "windows"; uv run pytest
    """
    family = QFontInfo(QFont("Segoe UI Variable Display")).family()
    if not family.startswith("Segoe"):
        pytest.skip(f"needs the real UI font, Qt resolved {family!r}")
