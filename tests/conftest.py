"""Shared fixtures.

Qt needs a platform plugin even with nothing to show; `offscreen` keeps the
render tests headless and stops windows from flashing on a developer machine.
The variable must be set before the first Qt import.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """One QApplication for the whole session; Qt forbids a second one."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def real_fonts(qapp) -> None:
    """Skip unless the layout was actually measured against the resolved font.

    The geometry constants (ring radius, column widths, the point sizes that
    make "100%" fit) were derived from one font's metrics. Three ways to end up
    measuring a different one: the offscreen plugin ships a stub font database
    whose fallback runs about 1.8x wider, Windows Server has Segoe UI but not
    the Variable Display cut, and macOS and Linux resolve their own families
    entirely.

    So the gate is not "did we get a font" but "did we get one of the fonts the
    numbers in widget.py were written for" - see `paint.MEASURED`. Porting the
    layout to another platform means measuring there and adding it to that set.

    Run the whole suite against the real thing with:

        $env:QT_QPA_PLATFORM = "windows"; uv run pytest     # Windows
        QT_QPA_PLATFORM=cocoa uv run pytest                 # macOS
        QT_QPA_PLATFORM=xcb uv run pytest                   # Linux
    """
    from claude_usage import paint

    resolved = paint.family()
    if resolved not in paint.MEASURED:
        pytest.skip(f"layout not measured for {resolved!r}; "
                    f"known: {', '.join(sorted(paint.MEASURED))}")
