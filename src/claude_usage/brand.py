"""The marks the panel wears, one per agent it can watch.

Clawd is Claude Code's own mark, drawn from the official SVG. The Codex slot is
not OpenAI's logo and must not become it: that is their trademark, and putting
it on a third-party gauge would be claiming an endorsement nobody gave. What
sits there instead is a mascot of this project's own, built in Clawd's language
so the two read as a set - blocky silhouette, eyes as holes in the path, one
flat colour, and the same y 5..20 band of the viewBox so every size and centring
calculation below works unchanged for both.

Both are embedded as strings so there is no data file for PyInstaller to miss.
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from . import theme

# The official Claude Code mark, with the fill parameterized. The two holes in
# the path (x 6..7.5 and 16.5..18) are its eyes.
_CLAWD = (
    "M20.998 10.949H24v3.102h-3v3.028h-1.487V20H18v-2.921h-1.487V20H15v-2.921H9V20"
    "H7.488v-2.921H6V20H4.487v-2.921H3V14.05H0V10.95h3V5h17.998v5.949zM6 10.949h1."
    "488V8.102H6v2.847zm10.51 0H18V8.102h-1.49v2.847z"
)

# Ours. A blocky head on two feet with a single stub antenna: the terminal
# creature a coding agent would be if it had a face. Straight edges only, so it
# survives being drawn thirteen pixels tall next to Clawd without turning to
# mush, and the eyes are holes in the same path so one fill colours all of it.
_ROBIT = (
    "M10.3 5h3.4v2.5H23v9.5h-3V20h-3.5v-2.9h-9V20H4v-2.9H1V7.5h9.3V5z"
    "M5.7 10.3h3.1v3.4H5.7v-3.4zm9.5 0h3.1v3.4h-3.1v-3.4z"
)

_SVG = (
    '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
    '<path clip-rule="evenodd" fill-rule="evenodd" fill="{fill}" d="{path}"/></svg>'
)

MARKS = {"claude": _CLAWD, "codex": _ROBIT}
FALLBACK = "claude"

_INK_HEIGHT = 15.0      # both drawings span y 5..20 of the 24-unit viewBox
_VIEWBOX = 24.0

_cache: dict[tuple[str, int, str, float], QPixmap] = {}


def mark(key: str, height: int, color: QColor = theme.ACCENT,
         dpr: float = 1.0) -> QPixmap:
    """The named agent's mark, `height` pixels tall, measured on the drawn band.

    The pixmap comes out taller than requested because the viewBox has empty
    rows above and below; that transparent slack is what centers the mascot on a
    text line. Pass the window's devicePixelRatioF so it stays crisp when
    Windows scaling is above 100%.
    """
    cache_key = (key, height, color.name(), dpr)
    if cache_key in _cache:
        return _cache[cache_key]

    box = height * _VIEWBOX / _INK_HEIGHT
    pm = QPixmap(int(box * dpr), int(box * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)

    path = MARKS.get(key, MARKS[FALLBACK])
    svg = _SVG.format(fill=color.name(), path=path)
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(p, QRectF(0, 0, box, box))
    p.end()

    _cache[cache_key] = pm
    return pm


def clawd(height: int, color: QColor = theme.ACCENT, dpr: float = 1.0) -> QPixmap:
    """Claude Code's mark. Kept as its own name because the icon generator and
    the widget's badge want that one specifically, not whichever is selected."""
    return mark("claude", height, color, dpr)
