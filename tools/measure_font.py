"""Does the layout still fit in a given font?

    uv run python tools/measure_font.py                     # the resolved family
    uv run python tools/measure_font.py "Inter"             # an installed family
    uv run python tools/measure_font.py path/to/Inter.ttf   # a file, not installed

The geometry constants in widget.py came from one font's metrics, and
`paint.MEASURED` records which. Everywhere else the app draws without anyone
having checked that "100%" clears the ring or that "56min" does not run into
the clock. This runs those checks and prints the numbers, so porting the layout
to another face is a measurement rather than a hope.

A font file is loaded into this process only, with QFontDatabase. Nothing is
installed and nothing on the system changes.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from claude_usage import paint
from claude_usage.theme import SM
from claude_usage.widget import (
    LABEL_W,
    RING_TEXT_MIN,
    RING_TEXT_PT,
    RING_TEXT_PT_WIDE,
    ring_text_fits,
    ring_text_pt,
)

# Exactly the pairs test_render.py checks. Inventing plausible-looking ones
# instead produced a failure for a row the widget cannot draw: the weekday form
# belongs to the panel, and never appears as a tail here.
ROWS = [
    ("2h13", "19:50"),       # the common case
    ("56min", "19:50"),      # minutes are half again as wide as hours
    ("38s", "1d22h"),
    ("100%", "6d23h"),       # widest value and widest tail together
]
PERCENTS = [0, 7, 38, 99, 100]
TRAY_LABELS = ["7", "16", "100"]
COL_W = 246 - 16 - 27 * 2 - 16 - 32 - SM      # the text column, from widget.py's layout


def load(argument: str) -> str:
    """Return the family to measure, loading a file first when given one."""
    path = Path(argument)
    if path.is_file():
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id == -1:
            raise SystemExit(f"Qt could not read {path}")
        families = QFontDatabase.applicationFontFamilies(font_id)
        if not families:
            raise SystemExit(f"{path} carries no family name")
        return families[0]
    return argument


def ring(pct: int) -> tuple[bool, str, str]:
    """The size the widget would settle on, and whether it had to shrink."""
    number = f"{pct:.0f}"
    size, unit = ring_text_pt(number)
    table = RING_TEXT_PT_WIDE[0] if len(number) > 2 else RING_TEXT_PT[0]
    note = f"{size}pt" + ("" if size == table else f" (down from {table})")
    return ring_text_fits(number, size, unit), note, f"min {RING_TEXT_MIN}pt"


def row(value: str, tail: str) -> tuple[bool, str, str]:
    """Mirrors test_row_value_never_reaches_the_tail, without building a widget."""
    used = (LABEL_W + paint.width(value, 11, QFont.Weight.DemiBold)
            + SM + paint.width(tail, 8))
    return used <= COL_W + 0.5, f"{used:.1f}px", f"{COL_W + 0.5:.1f}px"


def tray(label: str) -> tuple[bool, str, str]:
    """Mirrors test_tray_number_fits_the_small_icon."""
    from claude_usage.app import _fit_in_square

    w, h = paint.ink(label, _fit_in_square(label, 16), QFont.Weight.DemiBold)
    return max(w, h) <= 14, f"{max(w, h):.1f}px", "14.0px"


def main() -> int:
    app = QApplication(sys.argv[:1])          # the local reference keeps Qt alive
    wanted = load(sys.argv[1]) if len(sys.argv) > 1 else None

    if wanted:
        paint.set_family(wanted)
    resolved = paint.family()
    exact = QFont(resolved).exactMatch()
    print(f"{resolved}{'' if exact else '   (NOT an exact match - Qt substituted)'}")
    print(f"{'':32}{'is':>16}{'limit':>12}")

    failures = 0
    checks = (
        [(f'ring "{p}%"', ring(p)) for p in PERCENTS]
        + [(f'row "{v}" + "{t}"', row(v, t)) for v, t in ROWS]
        + [(f'tray "{label}"', tray(label)) for label in TRAY_LABELS]
    )
    for name, (passed, used, limit) in checks:
        failures += not passed
        print(f"  {'ok ' if passed else 'FAIL'} {name:<27}{used:>16}{limit:>12}")

    del app
    if failures:
        print(f"\n{failures} of {len(checks)} do not fit. The layout is not safe in "
              f"{resolved!r} as it stands.")
        return 1
    print(f"\nall {len(checks)} fit. {resolved!r} can be added to paint.MEASURED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
