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


@pytest.fixture(autouse=True)
def _never_the_real_config(monkeypatch, tmp_path) -> None:
    """No test may write into the user's own config directory.

    Two of them did before this existed. Anything that runs a collection cycle
    saves the burn-rate baseline, and a failed one appends to the error log;
    only the tests written alongside those features redirected the paths, so
    the rest wrote into %APPDATA% on the developer's machine and left sixteen
    fabricated failures in a log meant to be evidence.

    Autouse and here rather than per-file, because the next module to call
    _collect() will not remember either.
    """
    from agent_gauge import diag, poller

    monkeypatch.setattr(diag, "LOG_FILE", tmp_path / "errors.log")
    monkeypatch.setattr(poller, "HISTORY_FILE", tmp_path / "history.json")


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
    from agent_gauge import paint

    resolved = paint.family()
    if resolved not in paint.MEASURED:
        pytest.skip(f"layout not measured for {resolved!r}; "
                    f"known: {', '.join(sorted(paint.MEASURED))}")
