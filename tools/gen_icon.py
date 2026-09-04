"""Build the application icon from the same Clawd SVG the UI uses.

Three platforms want three shapes, so the output format follows the path:

    uv run python tools/gen_icon.py installer/claude-usage.ico     # Windows
    uv run python tools/gen_icon.py build/ClaudeUsage.iconset      # macOS
    uv run python tools/gen_icon.py build/icons                    # Linux

The .iconset is a directory in the layout `iconutil -c icns` expects; the macOS
build script runs that conversion, because Apple's own tool is the only way to
be sure the container is one macOS will accept. A bare directory gets the
freedesktop icon sizes for a hicolor theme.

Every size is rendered from the vector rather than downsampled from one large
bitmap: at 16 and 20 pixels the mascot is a handful of blocks, and resampling
turns them to mush.

The ICO container is assembled here instead of through Pillow on purpose:
importing PIL into a PySide6 process loads a second libpng/zlib, and Qt's PNG
encoder then dies with an access violation. Writing the container by hand is
some 40 lines and keeps the build free of that whole class of DLL clash.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath
from PySide6.QtWidgets import QApplication

from claude_usage import brand, theme

# Sizes Windows actually asks for: tray, taskbar, list views, tiles.
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
PNG_FROM = 64          # below this Windows is happiest with a plain DIB

# What iconutil reads. The @2x entries are a larger render under a smaller
# name, which is exactly what a Retina display asks for.
ICONSET = (
    ("icon_16x16.png", 16), ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32), ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128), ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256), ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512), ("icon_512x512@2x.png", 1024),
)

# freedesktop hicolor sizes: panels, launchers, alt-tab, settings.
HICOLOR = (16, 22, 24, 32, 48, 64, 128, 256, 512)


def render(size: int) -> QImage:
    """One square icon: rounded dark plate with the coral mascot centered."""
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    inset = max(size * 0.02, 0.5)
    plate = QPainterPath()
    plate.addRoundedRect(QRectF(inset, inset, size - inset * 2, size - inset * 2),
                         size * 0.22, size * 0.22)
    p.fillPath(plate, QColor(theme.SURFACE))

    mascot = brand.clawd(max(int(size * 0.52), 6), theme.ACCENT)
    p.drawPixmap(int((size - mascot.width()) / 2), int((size - mascot.height()) / 2), mascot)
    p.end()
    return img


def as_png(img: QImage) -> bytes:
    # QBuffer(QByteArray()) would keep a reference to a temporary that dies on
    # the next line; the no-arg constructor owns its buffer.
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


def as_dib(img: QImage) -> bytes:
    """BITMAPINFOHEADER + bottom-up BGRA rows + an empty AND mask.

    The header lies about the height (doubled) because the format predates
    alpha: it still expects the 1bpp mask to follow the color rows.
    """
    img = img.convertToFormat(QImage.Format.Format_ARGB32)
    w, h = img.width(), img.height()

    header = struct.pack("<IiiHHIIiiII", 40, w, h * 2, 1, 32, 0, 0, 0, 0, 0, 0)
    rows = [bytes(img.constScanLine(y))[: w * 4] for y in range(h - 1, -1, -1)]
    mask_stride = ((w + 31) // 32) * 4          # 1bpp rows padded to 4 bytes
    return header + b"".join(rows) + b"\x00" * (mask_stride * h)


def build(sizes: tuple[int, ...]) -> bytes:
    payloads = [as_png(render(s)) if s >= PNG_FROM else as_dib(render(s)) for s in sizes]

    header = struct.pack("<HHH", 0, 1, len(sizes))        # reserved, type=icon, count
    offset = len(header) + 16 * len(sizes)
    entries = b""
    for size, data in zip(sizes, payloads, strict=True):
        dim = 0 if size >= 256 else size                  # 0 means 256 in this field
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    return header + entries + b"".join(payloads)


def write_ico(out: Path) -> str:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(build(SIZES))
    return f"{out} ({', '.join(str(s) for s in SIZES)}), {out.stat().st_size / 1024:.1f} kB"


def write_iconset(out: Path) -> str:
    out.mkdir(parents=True, exist_ok=True)
    for name, size in ICONSET:
        (out / name).write_bytes(as_png(render(size)))
    return f"{out} ({len(ICONSET)} entries for iconutil)"


def write_hicolor(out: Path) -> str:
    """One PNG per size, plus the 256 copied to the flat name AppImage wants at
    the root of an AppDir."""
    for size in HICOLOR:
        target = out / f"{size}x{size}" / "apps"
        target.mkdir(parents=True, exist_ok=True)
        (target / "claude-usage-widget.png").write_bytes(as_png(render(size)))
    (out / "claude-usage-widget.png").write_bytes(as_png(render(256)))
    return f"{out} ({', '.join(str(s) for s in HICOLOR)})"


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "installer/claude-usage.ico")
    app = QApplication(sys.argv[:1])          # the local reference keeps Qt alive

    if out.suffix == ".ico":
        note = write_ico(out)
    elif out.suffix == ".iconset":
        note = write_iconset(out)
    else:
        note = write_hicolor(out)

    del app
    print(note)


if __name__ == "__main__":
    main()
