"""Drawing primitives shared by the widget, the panel and the tray icon."""
from __future__ import annotations

import math
import os
import sys

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetricsF,
    QPainter,
    QPainterPath,
    QPen,
)

from . import theme

# The UI font of each platform, best cut first. Only families a desktop ships
# by default are listed: a widget must never depend on the user having
# installed something.
#
# Linux is deliberately absent. It has no single default, every desktop already
# publishes the one it wants through QFontDatabase, and the list that used to
# be here led with Inter - which no desktop ships and which tools/measure_font.py
# shows to be the worst fit of the lot, running "38%" past the ring's stroke and
# truncating two of the four rows. Preferring it over the user's own configured
# font was wrong twice over.
CANDIDATES = {
    "win32": ("Segoe UI Variable Display", "Segoe UI"),
    "darwin": ("SF Pro Display", "SF Pro Text", "Helvetica Neue"),
}

# Families the layout has actually been measured in, with
# tools/measure_font.py. Anything else still renders - the gauge number sizes
# itself to whatever it is given - but the rows may truncate rather than fit,
# so the geometry tests skip instead of asserting.
MEASURED = frozenset({
    "Segoe UI Variable Display",     # the face the design was drawn against
    "Noto Sans",                     # all twelve checks fit
    "Ubuntu",                        # fits once the gauge number sizes itself
})

FONT_ENV = "AGENT_GAUGE_FONT"      # pin a family; also how the layout is measured

_family: str | None = None


def set_family(name: str | None) -> None:
    """Pin the family, or pass None to resolve it again.

    For tools/measure_font.py and the tests. The app never calls this: a user
    who wants a different face sets AGENT_GAUGE_FONT.
    """
    global _family
    _family = name


def family() -> str:
    """This platform's UI font family, resolved once.

    `exactMatch` rather than a name check: Qt happily hands back a substitute
    for a family it does not have, and measuring the wrong font is worse than
    knowing the preferred one is missing.
    """
    global _family
    if _family is None:
        forced = os.environ.get(FONT_ENV, "").strip()
        if forced:
            _family = forced
        else:
            for candidate in CANDIDATES.get(sys.platform, ()):
                if QFont(candidate).exactMatch():
                    _family = candidate
                    break
            else:
                # What the desktop itself is set to, which on Linux is the only
                # honest answer and everywhere else is a reasonable fallback.
                _family = QFontDatabase.systemFont(
                    QFontDatabase.SystemFont.GeneralFont).family()
    return _family


def font(size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """The platform UI font at `size` points, with tabular figures.

    Without `tnum` the digit 1 is narrower than the rest and the per-second
    countdown jitters as it re-renders.
    """
    f = QFont(family(), size)
    f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    f.setWeight(weight)
    f.setFeature(QFont.Tag("tnum"), 1)
    return f


def shadow(p: QPainter, rect: QRectF, radius: float, spread: float = 10.0,
           alpha: int = 46, dy: float = 3.0) -> None:
    """Hand-drawn shadow: concentric rounded rects at low alpha.

    QGraphicsDropShadowEffect on a translucent window freezes the content after
    the first frame on Windows, so the shadow is painted here instead. Each
    window reserves a transparent margin for it.
    """
    p.setPen(Qt.PenStyle.NoPen)
    steps = int(spread)
    for i in range(steps, 0, -1):
        t = i / steps
        col = QColor(0, 0, 0, max(int(alpha * (1.0 - t) ** 2), 1))
        path = QPainterPath()
        path.addRoundedRect(rect.adjusted(-i, -i + dy, i, i + dy), radius + i, radius + i)
        p.fillPath(path, col)


def surface(p: QPainter, rect: QRectF, radius: float = 14.0,
            fill: QColor = theme.SURFACE, border: QColor | None = theme.BORDER) -> None:
    """Base card: rounded fill with an optional hairline border."""
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    p.fillPath(path, fill)
    if border is not None:
        p.setPen(QPen(border, 1.0))
        p.drawPath(path)


def ring(p: QPainter, center: QPointF, radius: float, thickness: float, pct: float,
         color: QColor | None = None, track: QColor | None = theme.TRACK) -> None:
    """Progress ring starting at twelve o'clock, filling clockwise.

    With track=None only the filled arc is drawn, which is how the refresh ring
    orbits the gauge without reading as a second track.
    """
    pct = min(max(pct, 0.0), 100.0)
    color = color or theme.grad_color(pct)
    box = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)

    p.setBrush(Qt.BrushStyle.NoBrush)
    if track is not None:
        p.setPen(QPen(track, thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(box, 0, 360 * 16)

    if pct > 0:
        span = max(pct / 100.0 * 360.0, 2.0)   # keep a sliver visible above zero
        p.setPen(QPen(color, thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(box, 90 * 16, int(-span * 16))


def arc(p: QPainter, center: QPointF, radius: float, thickness: float,
        start_deg: float, span_deg: float, color: QColor) -> None:
    """Arc with a free start angle; 0 degrees at the top, growing clockwise."""
    box = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(color, thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawArc(box, int((90 - start_deg) * 16), int(-span_deg * 16))


def meter(p: QPainter, rect: QRectF, pct: float, segments: int = 18, gap: float = 3.0,
          color: QColor | None = None) -> None:
    """Segmented meter: eighteen blocks read as a quantity, a bar reads as a
    fraction, and a window filling up is a quantity."""
    pct = min(max(pct, 0.0), 100.0)
    color = color or theme.grad_color(pct)
    lit = int(pct / 100.0 * segments + 0.5)
    if pct > 0.5 and lit == 0:
        lit = 1

    seg_w = (rect.width() - gap * (segments - 1)) / segments
    radius = min(seg_w, rect.height()) / 2.5
    for i in range(segments):
        box = QRectF(rect.x() + i * (seg_w + gap), rect.y(), seg_w, rect.height())
        path = QPainterPath()
        path.addRoundedRect(box, radius, radius)
        p.fillPath(path, color if i < lit else theme.TRACK)


def bar(p: QPainter, rect: QRectF, pct: float, color: QColor | None = None) -> None:
    """Continuous bar over a track: the secondary reading, no segments."""
    pct = min(max(pct, 0.0), 100.0)
    radius = rect.height() / 2
    track = QPainterPath()
    track.addRoundedRect(rect, radius, radius)
    p.fillPath(track, theme.TRACK)
    if pct <= 0:
        return
    frac = max(pct / 100.0, rect.height() / rect.width())   # 1% still has to show
    progress(p, rect, frac, color or theme.grad_color(pct))


def progress(p: QPainter, rect: QRectF, frac: float, color: QColor, alpha: int = 255) -> None:
    """Progress sliver; disappears at zero instead of leaving an empty track."""
    frac = min(max(frac, 0.0), 1.0)
    if frac <= 0.01:
        return
    col = QColor(color)
    col.setAlpha(alpha)
    path = QPainterPath()
    bar_rect = QRectF(rect.x(), rect.y(), rect.width() * frac, rect.height())
    path.addRoundedRect(bar_rect, rect.height() / 2, rect.height() / 2)
    p.fillPath(path, col)


def numeric(p: QPainter, center: QPointF, number: str, unit: str, color: QColor,
            size: int, unit_size: int, unit_color: QColor | None = None) -> None:
    """Large number with a smaller unit attached, positioned by baseline.

    Two optical decisions:
    - center the number's ink (tightBoundingRect) rather than the font's line
      box, whose empty ascender and descender push the text visually low;
    - count only ~35% of the unit's width when centering horizontally, otherwise
      the "%" shoves the number off the middle of the ring.
    """
    f_num = font(size, QFont.Weight.DemiBold)
    f_unit = font(unit_size)
    fm_num = QFontMetricsF(f_num)
    ink = fm_num.tightBoundingRect(number)
    w_num = fm_num.horizontalAdvance(number)
    w_unit = QFontMetricsF(f_unit).horizontalAdvance(unit)

    baseline = center.y() - (ink.top() + ink.bottom()) / 2
    x = center.x() - (w_num + w_unit * 0.35) / 2

    p.setFont(f_num)
    p.setPen(color)
    p.drawText(QPointF(x, baseline), number)
    p.setFont(f_unit)
    p.setPen(unit_color or color)
    p.drawText(QPointF(x + w_num + 1, baseline), unit)


def hairline(p: QPainter, x0: float, x1: float, y: float,
             color: QColor = theme.BORDER) -> None:
    """One-pixel divider between content groups."""
    p.setPen(QPen(color, 1.0))
    p.drawLine(QPointF(x0, y), QPointF(x1, y))


def chip_width(label: str, size: int = 8, pad: float = 12.0) -> float:
    """Pill width derived from the label, so no box sits half empty."""
    return QFontMetricsF(font(size, QFont.Weight.DemiBold)).horizontalAdvance(label) + pad * 2


def chip(p: QPainter, rect: QRectF, label: str, color: QColor) -> None:
    """Status pill: washed-out fill in its own hue, text at full strength."""
    bg = QColor(color)
    bg.setAlpha(38)
    path = QPainterPath()
    path.addRoundedRect(rect, rect.height() / 2, rect.height() / 2)
    p.fillPath(path, bg)
    p.setPen(color)
    p.setFont(font(8, QFont.Weight.DemiBold))
    p.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)


def text(p: QPainter, rect: QRectF, s: str, color: QColor, size: int,
         weight: QFont.Weight = QFont.Weight.Normal,
         align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
         spacing: float = 0.0) -> None:
    f = font(size, weight)
    if spacing:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    p.setFont(f)
    p.setPen(color)
    p.drawText(rect, align, s)


def refresh_icon(p: QPainter, center: QPointF, radius: float, color: QColor,
                 thickness: float = 1.7) -> None:
    """Circular arrow, drawn rather than typed.

    Nearly a full turn with the head at the top: a wide gap and a small head
    read as a scratch at this size instead of as an arrow. A glyph would depend
    on whichever symbol font Windows resolves; this stays crisp at any DPI and
    matches the rest of the surface, which is all painted.
    """
    box = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(color, thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawArc(box, 105 * 16, 300 * 16)         # the gap is where the head goes

    head = math.radians(105)
    tip = QPointF(center.x() + radius * math.cos(head),
                  center.y() - radius * math.sin(head))
    forward = QPointF(math.sin(head), math.cos(head))   # clockwise travel
    outward = QPointF(math.cos(head), -math.sin(head))
    # Tied to the radius as well as the stroke: sized by thickness alone, the
    # head grew to nearly the width of the circle once the icon shrank.
    size = min(thickness * 2.2, radius * 0.7)

    arrow = QPainterPath()
    arrow.moveTo(tip.x() + forward.x() * size * 1.5, tip.y() + forward.y() * size * 1.5)
    arrow.lineTo(tip.x() + outward.x() * size, tip.y() + outward.y() * size)
    arrow.lineTo(tip.x() - outward.x() * size, tip.y() - outward.y() * size)
    arrow.closeSubpath()
    p.fillPath(arrow, color)


DOT_R = 1.6             # one dot, shared by the separator and the menu


def dot(p: QPainter, center: QPointF, color: QColor, r: float = DOT_R) -> None:
    """A single drawn dot. Text punctuation would scale with the font instead of
    matching the menu affordance."""
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawEllipse(center, r, r)


def dots(p: QPainter, center: QPointF, color: QColor, r: float = DOT_R,
         gap: float = 5.0) -> None:
    """Drawn "..." menu affordance, crisp at any DPI."""
    for i in (-1, 0, 1):
        dot(p, QPointF(center.x() + i * gap, center.y()), color, r)


def width(s: str, size: int, weight: QFont.Weight = QFont.Weight.Normal) -> float:
    """Advance width of `s`, for layouts that must reserve space for it."""
    return QFontMetricsF(font(size, weight)).horizontalAdvance(s)


def ink(s: str, size: int, weight: QFont.Weight = QFont.Weight.Normal) -> tuple[float, float]:
    """Width and height of the marks themselves, ignoring the font's empty
    ascender and descender - what matters when fitting text into a shape."""
    box = QFontMetricsF(font(size, weight)).tightBoundingRect(s)
    return box.width(), box.height()


def elide(s: str, limit: float, size: int,
          weight: QFont.Weight = QFont.Weight.Normal) -> str:
    """Truncate with an ellipsis to fit `limit` at the given point size."""
    return QFontMetricsF(font(size, weight)).elidedText(
        s, Qt.TextElideMode.ElideRight, int(limit))
