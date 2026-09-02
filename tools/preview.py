"""Render the widget and the panel to a PNG contact sheet.

    uv run python tools/preview.py [out.png]

No network and no visible windows: the widgets are painted without ever being
shown. It runs on the normal Windows platform plugin on purpose: under
QT_QPA_PLATFORM=offscreen Qt loses the system font database and every glyph
renders as a box.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from claude_usage import api, paint, theme, tokens
from claude_usage.panel import Panel
from claude_usage.poller import Snapshot
from claude_usage.settings import Settings
from claude_usage.widget import FloatingWidget

GAP = 20
BACKDROP = QColor("#08080A")


def snapshot(h5: float, d7: float, incidents: tuple[str, ...] = (), error: str = "") -> Snapshot:
    now = time.time()
    usage = api.Usage(
        h5=h5, d7=d7,
        h5_reset=int(now + 8040), d7_reset=int(now + 169200),
        status_overall=("rejected" if h5 >= 100 else
                        "allowed_warning" if h5 >= 90 else "allowed"),
        claim="five_hour", ok=not error, error=error,
    )
    return Snapshot(
        usage=usage,
        totals=tokens.TokenTotals(input=202_040, output=31_283,
                                  cache_read=6_029_281, sessions=2),
        incidents=list(incidents), subscription="max", error=error,
    )


def render(widget) -> QImage:
    """Paint a widget offscreen at 1x, transparent background."""
    img = QImage(widget.width(), widget.height(), QImage.Format.Format_ARGB32)
    img.setDevicePixelRatio(1.0)
    img.fill(Qt.GlobalColor.transparent)
    widget.render(img)
    return img


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "preview.png")
    QApplication(sys.argv[:1])
    settings = Settings()

    states = (
        snapshot(12, 4),
        snapshot(71, 34),
        snapshot(96, 88, ("Elevated error rates on the API",)),
        snapshot(0, 0, error="token recusado (401): rode `claude` para renovar"),
    )

    settings["compact"] = False
    frames = []
    for snap in states:
        widget = FloatingWidget(settings)
        widget.set_snapshot(snap)
        frames.append(render(widget))

    settings["compact"] = True
    compact_widget = FloatingWidget(settings)
    compact_widget.set_snapshot(snapshot(71, 34))
    compact = render(compact_widget)
    settings["compact"] = False

    panel = Panel(settings)
    panel.set_snapshot(snapshot(71, 34, ("Elevated error rates on the API",)), "~1h40")
    panel_img = render(panel)

    column_w = frames[0].width() + compact.width() + GAP
    column_h = sum(f.height() + GAP for f in frames)
    width = GAP + column_w + GAP + panel_img.width() + GAP
    height = GAP + max(column_h, panel_img.height() + GAP) + GAP

    sheet = QImage(width, height, QImage.Format.Format_ARGB32)
    sheet.fill(BACKDROP)
    p = QPainter(sheet)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    y = GAP
    for frame in frames:
        p.drawImage(GAP, y, frame)
        y += frame.height() + GAP
    p.drawImage(GAP + frames[0].width() + GAP, GAP, compact)
    p.drawImage(GAP + column_w + GAP, GAP, panel_img)
    paint.text(p, QRectF(0, height - 20, width, 16), "preview offline · dados sintéticos",
               theme.FAINT, 8, align=Qt.AlignmentFlag.AlignHCenter)
    p.end()

    sheet.save(str(out))
    print(f"{out} ({width}x{height})")


if __name__ == "__main__":
    main()
