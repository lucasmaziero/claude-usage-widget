"""Clawd, the Claude Code mascot, drawn from the official SVG.

The two holes in the path (x 6..7.5 and 16.5..18) are its eyes. The SVG is
embedded as a string so there is no data file for PyInstaller to miss.
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from . import theme

# The official Claude Code mark, with the fill parameterized.
_SVG = (
    '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
    '<path clip-rule="evenodd" fill-rule="evenodd" fill="{fill}" d="'
    "M20.998 10.949H24v3.102h-3v3.028h-1.487V20H18v-2.921h-1.487V20H15v-2.921H9V20"
    "H7.488v-2.921H6V20H4.487v-2.921H3V14.05H0V10.95h3V5h17.998v5.949zM6 10.949h1."
    "488V8.102H6v2.847zm10.51 0H18V8.102h-1.49v2.847z"
    '"/></svg>'
)
_INK_HEIGHT = 15.0      # the drawing spans y 5..20 of the 24-unit viewBox
_VIEWBOX = 24.0

_cache: dict[tuple[int, str, float], QPixmap] = {}


def clawd(height: int, color: QColor = theme.ACCENT, dpr: float = 1.0) -> QPixmap:
    """Clawd `height` pixels tall, measured on the drawn band.

    The pixmap comes out taller than requested because the viewBox has empty
    rows above and below; that transparent slack is what centers the mascot on a
    text line. Pass the window's devicePixelRatioF so it stays crisp when
    Windows scaling is above 100%.
    """
    key = (height, color.name(), dpr)
    if key in _cache:
        return _cache[key]

    box = height * _VIEWBOX / _INK_HEIGHT
    pm = QPixmap(int(box * dpr), int(box * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)

    renderer = QSvgRenderer(QByteArray(_SVG.format(fill=color.name()).encode()))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(p, QRectF(0, 0, box, box))
    p.end()

    _cache[key] = pm
    return pm
