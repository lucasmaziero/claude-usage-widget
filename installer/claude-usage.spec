# PyInstaller build definition. Driven by installer/build.ps1.
#
# onedir, not onefile: onefile unpacks the whole Qt runtime into %TEMP% on every
# launch, which is a second or two of startup for an app that lives in the tray
# and is expected to start with Windows. The installer hides the folder anyway.
import tomllib
from pathlib import Path

ROOT = Path(SPECPATH).parent  # noqa: F821 - SPECPATH is injected by PyInstaller

# The version lives in pyproject.toml and nowhere else; the resource embedded in
# the .exe (Properties > Details) is rendered from it at build time.
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
FIELDS = tuple(int(part) for part in VERSION.split(".")) + (0,) * (4 - VERSION.count(".") - 1)

VERSION_FILE = ROOT / "build" / "work" / "version.txt"
VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
VERSION_FILE.write_text(
    f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={FIELDS}, prodvers={FIELDS}, mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Lucas Maziero'),
      StringStruct('FileDescription', 'Claude Usage Widget'),
      StringStruct('FileVersion', '{VERSION}'),
      StringStruct('InternalName', 'ClaudeUsage'),
      StringStruct('LegalCopyright', 'Copyright (c) 2026 Lucas Maziero. MIT License.'),
      StringStruct('OriginalFilename', 'ClaudeUsage.exe'),
      StringStruct('ProductName', 'Claude Usage Widget'),
      StringStruct('ProductVersion', '{VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
    encoding="utf-8",
)

# PySide6-Essentials ships far more than this app touches. It only needs
# QtCore/QtGui/QtWidgets (UI), QtNetwork (single-instance socket) and QtSvg
# (the Clawd mascot).
EXCLUDES = [
    "PySide6.Qt3DAnimation", "PySide6.Qt3DCore", "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput", "PySide6.Qt3DLogic", "PySide6.Qt3DRender",
    "PySide6.QtBluetooth", "PySide6.QtCharts", "PySide6.QtConcurrent",
    "PySide6.QtDataVisualization", "PySide6.QtDBus", "PySide6.QtDesigner",
    "PySide6.QtHelp", "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetworkAuth", "PySide6.QtNfc", "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning", "PySide6.QtPrintSupport", "PySide6.QtQml",
    "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets", "PySide6.QtRemoteObjects", "PySide6.QtScxml",
    "PySide6.QtSensors", "PySide6.QtSerialBus", "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio", "PySide6.QtSql", "PySide6.QtStateMachine",
    "PySide6.QtTest", "PySide6.QtTextToSpeech", "PySide6.QtUiTools",
    "PySide6.QtWebChannel", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets", "PySide6.QtWebSockets", "PySide6.QtXml",
    # stdlib corners the app never reaches
    "tkinter", "unittest", "pydoc", "doctest", "test", "distutils",
]

a = Analysis(  # noqa: F821
    [str(ROOT / "installer" / "entry.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[],
    hiddenimports=[],
    excludes=EXCLUDES,
    noarchive=False,
)

# Mesa's software OpenGL fallback is 20 MB, a fifth of the bundle, and this app
# paints through the raster engine only.
a.binaries = [b for b in a.binaries if "opengl32sw" not in b[0].lower()]

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ClaudeUsage",
    console=False,                       # tray app: a console window would be noise
    icon=str(ROOT / "installer" / "claude-usage.ico"),
    version=str(VERSION_FILE),
    debug=False,
    strip=False,
    upx=False,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ClaudeUsage",
)
