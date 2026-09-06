#!/usr/bin/env bash
#
# Builds the icon, the frozen app and the distributable, for macOS and Linux.
# The Windows counterpart is installer/build.ps1.
#
#   uv sync
#   ./installer/build.sh
#
# macOS produces build/AgentGauge-<version>-<arch>.dmg, holding a bundle that
# LSUIElement keeps out of the Dock. Linux produces
# build/AgentGauge-<version>.AppImage. Either way build/dist holds the
# unpacked app, which is the portable form.
#
# Options:
#   --skip-package   stop after the frozen app
#   --clean          wipe build/ first, including PyInstaller's caches
#
# Signing (macOS): CODESIGN_ID defaults to "-", an ad-hoc signature. That is not
# optional on Apple Silicon - an unsigned arm64 binary is killed on launch - but
# it is not a Developer ID either, so Gatekeeper still shows the unidentified
# developer warning. Set CODESIGN_ID to a real identity to sign properly.
set -euo pipefail

skip_package=0
clean=0
for arg in "$@"; do
    case "$arg" in
        --skip-package) skip_package=1 ;;
        --clean)        clean=1 ;;
        *) echo "unknown option: $arg" >&2; exit 2 ;;
    esac
done

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"

cyan=$'\033[36m'; green=$'\033[32m'; grey=$'\033[90m'; off=$'\033[0m'
say() { printf '%s==> %s%s\n' "$cyan" "$1" "$off"; }
note() { printf '%s    %s%s\n' "$grey" "$1" "$off"; }

# The version lives in pyproject.toml; nothing else may declare it.
version=$(sed -n 's/^version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' pyproject.toml | head -1)
[ -n "$version" ] || { echo "could not read version from pyproject.toml" >&2; exit 1; }

arch=$(uname -m)
case "$(uname -s)" in
    Darwin) os=macos ;;
    Linux)  os=linux ;;
    *) echo "build.sh covers macOS and Linux; use installer/build.ps1 on Windows" >&2; exit 2 ;;
esac

printf '%sAgent Gauge %s (%s %s)%s\n' "$cyan" "$version" "$os" "$arch" "$off"

if [ "$clean" -eq 1 ] && [ -d build ]; then
    say clean
    rm -rf build
fi

# ------------------------------------------------------------------- icon
say icon
if [ "$os" = macos ]; then
    rm -rf build/AgentGauge.iconset
    uv run python tools/gen_icon.py build/AgentGauge.iconset
    # iconutil rather than a hand-rolled container: Apple's tool is the only
    # thing that is certainly producing an .icns macOS will accept.
    iconutil -c icns -o build/AgentGauge.icns build/AgentGauge.iconset
    note "build/AgentGauge.icns"
else
    uv run python tools/gen_icon.py build/icons
fi

# -------------------------------------------------------------- frozen app
say "frozen app"
uv run --extra build pyinstaller installer/agent-gauge.spec \
    --noconfirm --distpath build/dist --workpath build/work --log-level WARN

if [ "$os" = macos ]; then
    app="build/dist/Agent Gauge.app"
    [ -d "$app" ] || { echo "expected $app" >&2; exit 1; }

    # PyInstaller signs the individual binaries; this seals the bundle, which is
    # what the loader actually checks.
    say "sign as ${CODESIGN_ID:--}"
    codesign --force --deep --timestamp=none \
             --sign "${CODESIGN_ID:--}" "$app"

    # Informational, not a gate. PyInstaller signs the nested binaries and this
    # seals the bundle over them, which --strict can flag while the app still
    # launches. A signature that is genuinely broken shows up as the app being
    # killed on open, which no amount of verifying here would have caught.
    codesign --verify --deep --strict "$app" || \
        printf '%s    codesign --verify complained; test the .dmg by hand%s\n' "$grey" "$off"
    payload="$app"
else
    payload="build/dist/AgentGauge"
    [ -x "$payload/AgentGauge" ] || { echo "expected $payload/AgentGauge" >&2; exit 1; }
fi

note "$payload ($(du -sh "$payload" | cut -f1))"

if [ "$skip_package" -eq 1 ]; then
    printf '%sskipping package (--skip-package)%s\n' "$grey" "$off"
    exit 0
fi

# ---------------------------------------------------------------- package
# One artifact in build/, always the current one. Stale versions from earlier
# runs are the easiest thing in the world to ship by accident.
rm -f build/AgentGauge-*.dmg build/AgentGauge-*.AppImage

if [ "$os" = macos ]; then
    say dmg
    out="build/AgentGauge-$version-$arch.dmg"
    stage=build/work/dmg
    rm -rf "$stage"
    mkdir -p "$stage"
    cp -R "$app" "$stage/"
    ln -s /Applications "$stage/Applications"      # the drag-here target
    hdiutil create -volname "Agent Gauge" -srcfolder "$stage" \
                   -ov -format UDZO -quiet "$out"
else
    say appimage
    out="build/AgentGauge-$version.AppImage"
    appdir=build/work/AppDir
    rm -rf "$appdir"
    mkdir -p "$appdir/usr/bin" "$appdir/usr/share/applications"

    cp -R build/dist/AgentGauge "$appdir/usr/bin/"

    hicolor="$appdir/usr/share/icons/hicolor"
    mkdir -p "$hicolor"
    for dir in build/icons/*x*; do cp -R "$dir" "$hicolor/"; done
    # AppImage also wants the icon loose at the root, named after the .desktop.
    cp build/icons/agent-gauge.png "$appdir/agent-gauge.png"

    cat > "$appdir/agent-gauge.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Agent Gauge
Comment=Claude Code rate-limit usage on a floating desktop widget
Exec=AgentGauge
Icon=agent-gauge
Categories=Utility;Monitor;
Terminal=false
DESKTOP
    cp "$appdir/agent-gauge.desktop" "$appdir/usr/share/applications/"

    cat > "$appdir/AppRun" <<'APPRUN'
#!/bin/sh
# readlink -f, because an AppImage is normally reached through a symlink and
# $0 would otherwise point outside the mounted image.
HERE=$(dirname "$(readlink -f "$0")")
exec "$HERE/usr/bin/AgentGauge/AgentGauge" "$@"
APPRUN
    chmod +x "$appdir/AppRun"

    tool=build/work/appimagetool
    if [ ! -x "$tool" ]; then
        note "fetching appimagetool"
        curl -fsSL -o "$tool" \
            "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$arch.AppImage"
        chmod +x "$tool"
    fi
    # --appimage-extract-and-run: CI runners have no FUSE, and appimagetool is
    # itself an AppImage.
    ARCH="$arch" "$tool" --appimage-extract-and-run "$appdir" "$out" >/dev/null
fi

printf '%s    %s (%s)%s\n' "$green" "$out" "$(du -h "$out" | cut -f1)" "$off"
