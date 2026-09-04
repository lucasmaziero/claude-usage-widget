"""Collection thread: token -> API -> local transcripts -> signal to the UI."""
from __future__ import annotations

import contextlib
import threading
import time
from collections import deque
from dataclasses import dataclass, field

from PySide6.QtCore import QThread, Signal

from . import api, credentials, signin, tokens
from .i18n import t


@dataclass
class Snapshot:
    """Everything the UI needs to paint one cycle."""

    usage: api.Usage = field(default_factory=api.Usage)
    totals: tokens.TokenTotals = field(default_factory=tokens.TokenTotals)
    incidents: list[str] = field(default_factory=list)
    subscription: str = ""
    error: str = ""
    setup: str = ""            # signin.INSTALL or signin.SIGNIN, else empty
    at: float = field(default_factory=time.time)

    @property
    def ok(self) -> bool:
        return self.usage.ok and not self.error


class Poller(QThread):
    """Polls every `interval` seconds; refresh() wakes it immediately.

    Receivers must be QObjects: connected to a plain Python callable the
    connection becomes direct and painting would run on this thread.
    """

    updated = Signal(object)   # Snapshot
    busy = Signal(bool)        # True while a cycle is in flight

    STATUS_EVERY = 300         # incidents move slowly; every 5 min is plenty
    HISTORY_MAX = 180          # ~6h of samples at the default interval

    def __init__(self, interval: int, parent=None) -> None:
        super().__init__(parent)
        self._interval = interval
        self._wake = threading.Event()
        self._stop = False
        self._last_status = 0.0
        self._incidents: list[str] = []
        self.history: deque[tuple[float, float]] = deque(maxlen=self.HISTORY_MAX)

    def set_interval(self, seconds: int) -> None:
        self._interval = seconds
        self._wake.set()

    def refresh(self) -> None:
        self._wake.set()

    def stop(self) -> None:
        self._stop = True
        self._wake.set()

    def run(self) -> None:
        while not self._stop:
            self.busy.emit(True)
            snap = self._collect()
            self.updated.emit(snap)   # data first, so the spinner stops on fresh values
            self.busy.emit(False)
            self._wake.wait(self._interval)
            self._wake.clear()

    def _collect(self) -> Snapshot:
        try:
            creds = credentials.load()
        except credentials.CredentialsError as exc:
            # Two dead ends wear the same exception. "Run `claude` to sign in"
            # is wrong advice for someone who has never installed it, so the
            # message is chosen here rather than where the file was missed.
            need = signin.needed()
            message = t("error.no_claude") if need == signin.INSTALL else str(exc)
            return Snapshot(error=message, setup=need)

        usage = api.fetch_usage(creds.token)
        snap = Snapshot(usage=usage, subscription=creds.subscription,
                        error="" if usage.ok else usage.error)

        if usage.ok:
            self.history.append((time.time(), usage.h5))
            with contextlib.suppress(OSError):
                snap.totals = tokens.collect(tokens.window_start(usage.h5_reset))

        now = time.time()
        if now - self._last_status >= self.STATUS_EVERY:
            self._incidents = api.fetch_incidents()
            self._last_status = now
        snap.incidents = list(self._incidents)
        return snap

    def burn_rate(self) -> float:
        """Percentage points per hour on the 5h window, from this session's samples.

        Returns 0 while there is no baseline yet, and after a window reset drops
        the percentage back down.
        """
        if len(self.history) < 2:
            return 0.0
        t0, p0 = self.history[0]
        t1, p1 = self.history[-1]
        dt = (t1 - t0) / 3600.0
        if dt < 0.05 or p1 < p0:      # under 3 min of baseline, or the window reset
            return 0.0
        return (p1 - p0) / dt

    def projection(self, usage: api.Usage) -> str:
        """When usage would hit 100% at the current rate: '~1h40', or '' if the
        answer would be noise: no baseline, or the window resets first."""
        rate = self.burn_rate()
        if rate <= 0.1 or usage.h5 >= 100:
            return ""
        hours = (100.0 - usage.h5) / rate
        left = (usage.h5_reset - time.time()) / 3600.0 if usage.h5_reset else 0
        if left and hours > left:
            return ""
        if hours >= 1:
            return f"~{int(hours)}h{int((hours % 1) * 60):02d}"
        return f"~{int(hours * 60)}min"
