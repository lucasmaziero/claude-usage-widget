"""Expanded panel: the detail view, as a popup that closes on an outside click.

Deliberate hierarchy: the 5h window is what bites first, so it gets a card and
the big number; the 7-day window is supporting information and sits directly on
the surface, with no card of its own. A hairline separates the metadata strip.
"""
from __future__ import annotations

import time

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QFont, QPainter
from PySide6.QtWidgets import QWidget

from . import brand, paint, providers, signin, theme
from .i18n import t, tn
from .poller import Snapshot
from .theme import LG, MD, SM

W, H = 340, 326              # visible card
M = 16                       # transparent margin reserved for the shadow
PAD = LG
CARD_H = 112
COL = W - PAD * 2            # usable content width

HEAD_Y = LG
PRIMARY_Y = 44
SECONDARY_Y = PRIMARY_Y + CARD_H + MD
DIVIDER_Y = 228
STRIP_Y = 236
INCIDENT_Y = 260
REFRESH_W = 76


class Panel(QWidget):
    refresh_requested = Signal()
    setup_requested = Signal()          # the way out when there is no token

    def __init__(self, settings) -> None:
        super().__init__(None)
        self.settings = settings
        self.snap: Snapshot | None = None
        self.projection = ""
        self._hover_refresh = False
        self._hover_setup = False
        self._hidden_at = 0.0

        self.setWindowFlags(
            Qt.WindowType.Popup                 # closes itself on an outside click
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFixedSize(W + M * 2, H + M * 2)

    # ------------------------------------------------------------ placement
    def popup_at(self, anchor: QRectF | None, screen) -> None:
        """Open against the widget, flipping below it when there is no room above."""
        geo = screen.availableGeometry()
        w, h = self.width(), self.height()
        if anchor is None:
            x, y = geo.right() - w, geo.bottom() - h
        else:
            x = int(anchor.center().x() - w / 2)
            y = int(anchor.top() - h + M)
            if y < geo.top():
                y = int(anchor.bottom() - M)
        x = min(max(x, geo.left() - M), geo.right() - w + M)
        y = min(max(y, geo.top() - M), geo.bottom() - h + M)
        self.move(QPoint(x, y))
        self.show()

    def hideEvent(self, event) -> None:
        self._hidden_at = time.monotonic()
        super().hideEvent(event)

    def just_closed(self, window: float = 0.25) -> bool:
        """A click on the widget while the panel is open arrives in two parts:
        the popup closes itself, then the widget receives the same click. Without
        this guard that second event would reopen the panel."""
        return time.monotonic() - self._hidden_at < window

    def set_snapshot(self, snap: Snapshot, projection: str = "") -> None:
        self.snap = snap
        self.projection = projection
        self.update()

    def _refresh_zone(self) -> QRectF:
        """Hit area of the "atualizar agora" link, in window coordinates."""
        return QRectF(M + W - PAD - REFRESH_W, M + H - PAD - 20, REFRESH_W, 20)

    def _setup_label(self) -> str:
        """Empty unless the user is stuck without a token."""
        if not (self.snap and self.snap.setup):
            return ""
        key = "panel.get_claude" if self.snap.setup == signin.INSTALL else "panel.how_signin"
        return t(key) + "  →"

    def _setup_zone(self) -> QRectF:
        """Hit area of the setup link, measured rather than fixed: it shares the
        footer with the refresh link and the two labels differ per language."""
        label = self._setup_label()
        if not label:
            return QRectF()
        width, _ = paint.ink(label, 8, QFont.Weight.DemiBold)
        return QRectF(M + PAD, M + H - PAD - 20, min(width + 6, COL - REFRESH_W - SM), 20)

    # -------------------------------------------------------------- painting
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        card = QRectF(M, M, W, H)
        paint.shadow(p, card, 18.0, spread=M - 2, alpha=64, dy=4.0)
        paint.surface(p, card, radius=18.0)
        p.translate(M, M)                     # from here on, card coordinates

        snap = self.snap
        live = bool(snap and snap.ok)
        u = snap.usage if live else None
        now = time.time()
        right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        self._header(p, snap, right)
        self._primary(p, QRectF(PAD, PRIMARY_Y, COL, CARD_H), u, now)
        self._secondary(p, QRectF(PAD, SECONDARY_Y, COL, 48), u, now)
        paint.hairline(p, PAD, W - PAD, DIVIDER_Y)
        self._metadata(p, snap, right)
        self._footer(p, snap, right)
        p.end()

    def _header(self, p: QPainter, snap: Snapshot | None, right) -> None:
        head = QRectF(PAD, HEAD_Y, COL, 20)
        provider = providers.get(str(self.settings["provider"]))

        # Each agent wears its own mark, and the mark goes gray with the same
        # signal as before. Which one is drawn is the header's way of saying
        # whose numbers these are, so it follows the selection rather than the
        # app: Clawd over Codex's percentages would be a lie about the source.
        unwell = bool(snap and (snap.error or snap.incidents))
        icon = brand.mark(provider.key, 13, theme.FAINT if unwell else theme.ACCENT,
                          self.devicePixelRatioF())
        icon_h = icon.height() / icon.devicePixelRatio()
        p.drawPixmap(QPointF(PAD, head.center().y() - icon_h / 2), icon)
        offset = icon.width() / icon.devicePixelRatio() + SM

        paint.text(p, head.adjusted(offset, 0, 0, 0), provider.label.upper(),
                   theme.TEXT, 9, QFont.Weight.DemiBold, spacing=1.2)
        paint.text(p, head, (snap.subscription if snap else "").upper() or theme.NO_DATA,
                   theme.ACCENT, 8, QFont.Weight.DemiBold, align=right, spacing=1.0)

    def _primary(self, p: QPainter, rect: QRectF, u, now: float) -> None:
        """5h window: its own card, big number, full segmented meter."""
        paint.surface(p, rect, radius=14.0, fill=theme.SURFACE2, border=None)
        inner = rect.adjusted(LG, MD, -LG, -MD)
        right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        # Tall enough for the 24pt font, whose line box is ~43px: inside a 24px
        # rect Qt clips the ascender and descender.
        head = QRectF(inner.x(), inner.y() - 2, inner.width(), 44)
        paint.text(p, head, t("panel.window_5h"), theme.MUTED, 9)
        paint.text(p, head, f"{u.h5:.0f}%" if u else theme.NO_DATA,
                   theme.grad_color(u.h5) if u else theme.FAINT,
                   24, QFont.Weight.DemiBold, align=right)

        paint.meter(p, QRectF(inner.x(), inner.y() + 48, inner.width(), 10),
                    u.h5 if u else 0.0)

        foot = QRectF(inner.x(), inner.bottom() - LG, inner.width(), LG)
        if not u:
            paint.text(p, foot, t("panel.waiting"), theme.FAINT, 8)
            return
        paint.text(p, foot, t("panel.resets", clock=theme.fmt_clock(u.h5_reset),
                              left=theme.fmt_countdown(u.h5_reset, now)), theme.MUTED, 8)
        if self.projection:
            paint.text(p, foot, t("panel.overflows", projection=self.projection),
                       theme.WARN, 8, QFont.Weight.DemiBold, align=right)

    def _secondary(self, p: QPainter, rect: QRectF, u, now: float) -> None:
        """7-day window: supporting, no card, continuous bar instead of segments."""
        right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        head = QRectF(rect.x(), rect.y(), rect.width(), 18)
        paint.text(p, head, t("panel.window_7d"), theme.MUTED, 9)
        paint.text(p, head, f"{u.d7:.0f}%" if u else theme.NO_DATA,
                   theme.grad_color(u.d7) if u else theme.FAINT,
                   13, QFont.Weight.DemiBold, align=right)

        paint.bar(p, QRectF(rect.x(), rect.y() + 24, rect.width(), 4), u.d7 if u else 0.0)

        if not u:
            return
        foot = QRectF(rect.x(), rect.y() + 32, rect.width(), 16)
        paint.text(p, foot, t("panel.resets_on", weekday=theme.fmt_weekday(u.d7_reset),
                              clock=theme.fmt_clock(u.d7_reset),
                              left=theme.fmt_countdown(u.d7_reset, now)), theme.FAINT, 8)
        if u.claim == "seven_day":
            paint.text(p, foot, t("panel.bottleneck"), theme.WARN, 8,
                       QFont.Weight.DemiBold, align=right)

    def _metadata(self, p: QPainter, snap: Snapshot | None, right) -> None:
        """Status chip, window token counts, and any open incident."""
        strip = QRectF(PAD, STRIP_Y, COL, 20)
        label, color = theme.status_label(snap.usage) if snap else ("SEM DADOS", theme.FAINT)
        paint.chip(p, QRectF(strip.x(), strip.y(), paint.chip_width(label), 20), label, color)
        paint.text(p, strip, self._tokens_line(snap), theme.MUTED, 8, align=right)

        line = QRectF(PAD, INCIDENT_Y, COL, 18)
        if snap and snap.error:
            paint.text(p, line, paint.elide(snap.error, COL, 8),
                       theme.MUTED if snap.waiting else theme.BAD, 8)
        elif snap and snap.incidents:
            paint.text(p, line, paint.elide("! " + snap.incidents[0], COL, 8), theme.WARN, 8)
        else:
            host = providers.get(str(self.settings["provider"])).status_host
            paint.text(p, line, t("panel.no_incidents", host=host), theme.FAINT, 8)

    def _footer(self, p: QPainter, snap: Snapshot | None, right) -> None:
        foot = QRectF(PAD, H - PAD - 20, COL, 20)
        label = self._setup_label()
        if label:
            # With no token there is nothing worth timestamping, so the slot
            # carries the way out instead of the hour a failure last repeated.
            paint.text(p, foot, label,
                       theme.ACCENT if self._hover_setup else theme.MUTED, 8,
                       QFont.Weight.DemiBold)
        else:
            stamp = time.strftime("%H:%M:%S", time.localtime(snap.at)) if snap else "--:--:--"
            chosen = int(self.settings["poll_sec"])
            every = snap.interval if snap and snap.interval else chosen
            cadence = f"{every}s" if every < 60 else f"{every // 60}min"
            # Marked when it is not what the menu says, so a fetch that looks
            # overdue reads as a decision rather than a stall.
            key = "panel.updated_idle" if every > chosen else "panel.updated"
            paint.text(p, foot, t(key, stamp=stamp, cadence=cadence), theme.FAINT, 8)
        paint.text(p, self._refresh_zone().translated(-M, -M), t("panel.refresh_now"),
                   theme.ACCENT if self._hover_refresh else theme.MUTED, 8, align=right)

    def _tokens_line(self, snap: Snapshot | None) -> str:
        if not snap or not snap.totals.sessions:
            return t("panel.no_transcripts")
        totals = snap.totals
        return tn(totals.sessions, "panel.tokens_one", "panel.tokens_other",
                  total=theme.fmt_tokens(totals.total),
                  cache=theme.fmt_tokens(totals.cache_read))

    # ----------------------------------------------------------------- mouse
    def mouseMoveEvent(self, event) -> None:
        where = event.position()
        refresh = self._refresh_zone().contains(where)
        setup = self._setup_zone().contains(where)
        if refresh != self._hover_refresh or setup != self._hover_setup:
            self._hover_refresh, self._hover_setup = refresh, setup
            self.setCursor(Qt.CursorShape.PointingHandCursor if refresh or setup
                           else Qt.CursorShape.ArrowCursor)
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        where = event.position()
        if self._refresh_zone().contains(where):
            self.refresh_requested.emit()
        elif self._setup_zone().contains(where):
            self.setup_requested.emit()
