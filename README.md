<div align="center">

# Claude Usage Widget

**Your Claude Code limits, on a floating desktop widget.**

**English** · [Português](README.pt-BR.md)

[![CI](https://github.com/lucasmaziero/claude-usage-widget/actions/workflows/ci.yml/badge.svg)](https://github.com/lucasmaziero/claude-usage-widget/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/lucasmaziero/claude-usage-widget)](https://github.com/lucasmaziero/claude-usage-widget/releases/latest)
[![Python](https://img.shields.io/badge/python-3.11+-3776ab)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

<img src="docs/widget.png" width="440" alt="Floating widget showing 41% of the 5-hour window">

</div>

---

## How it works

The Anthropic API exposes no usage endpoint for subscription accounts. Utilization rides along in
the `anthropic-ratelimit-unified-*` headers of any response, so the widget sends the smallest
request it can, a `POST /v1/messages` with `max_tokens: 1`, purely to read them:

| Header | Becomes |
| --- | --- |
| `unified-5h-utilization` | percentage of the 5-hour window |
| `unified-7d-utilization` | percentage of the 7-day window |
| `unified-5h-reset` / `unified-7d-reset` | clock and countdown for each reset |
| `unified-status` / `representative-claim` | status chip, and which window binds |

Two things follow from the app running on the **same machine** as Claude Code:

- **Nothing to configure.** The OAuth token comes from `%USERPROFILE%\.claude\.credentials.json`,
  the same file Claude Code uses, re-read on every cycle. When Claude Code refreshes the token, the
  widget follows on its own.
- **Real token counts.** The headers only carry percentages; the absolute numbers exist only in the
  transcripts under `~/.claude/projects/**/*.jsonl`, which are read straight off the disk.

## Installation

Download `ClaudeUsage-Setup-<version>.exe` from the [releases page][releases] and double-click it.
The install is **per user**, into `%LOCALAPPDATA%\Programs\Claude Usage Widget`. No admin, no UAC
prompt. The wizard offers a desktop shortcut and starting with Windows, both optional. It uninstalls
from **Installed apps** like any program, asking first whether to remove your preferences too.

The installer is not signed, so SmartScreen warns about an "unknown publisher" on the first
download. A SHA-256 is published beside each release for anyone who wants to verify the file.

Requires Claude Code to have been signed in on the machine (`claude` once). Without it the widget
shows `.credentials.json not found: run claude once to sign in`.

[releases]: https://github.com/lucasmaziero/claude-usage-widget/releases/latest

### From source

```powershell
uv sync
uv run claude-usage      # or .\run.bat, which starts it without a console window
```

## Usage

<img src="docs/panel.png" width="380" align="right" alt="Expanded panel">

**Widget.** No number appears twice: the ring answers *how much of the 5-hour window is spent*, the
`5h` row answers *how long until it resets* (with the reset clock on the right), and the `7d` row
covers the week.

A second ring orbits the gauge, gray over a track, counting down to the next fetch, and it turns
into a green spinner while the fetch runs. The gray is deliberate: at high usage the gauge goes
amber or red, and a concentric ring in the same color family melts into it.

The right column has three floors: the mascot on top, the **refresh** button in the middle, the menu
at the bottom. Drag the rest of the card to move it (the position is saved), click to open the
panel, or right-click anywhere for the menu.

**Panel.** The 5-hour window is what bites first, so it gets a card with the big number and an
eighteen-segment meter; the 7-day window is supporting information and sits directly on the surface
with a continuous bar. Below a hairline come the metadata: status chip (`OK` / `WARNING` /
`BLOCKED`), real token counts for the window, open incidents from `status.claude.com`, and the
timestamp of the last fetch.

The mascot in the header goes gray on a fetch error or an open incident, the same signal the
widget's badge gives.

**Tray.** The icon is the ring with the number inside, drawn one size at a time so the shell never
has to shrink it, including the in-between sizes display scaling asks for (25px at 125%). The
tooltip carries both windows.

<br clear="right">

<div align="center"><img src="docs/tray.png" width="260" alt="Tray icon at 6%, 47%, 83% and 100%"></div>

### Menu

| Item | What it does |
| --- | --- |
| Refresh now | Forces a cycle outside the interval |
| Open panel | Same as clicking the widget |
| Show widget | Leaves only the tray icon |
| Compact mode | Shrinks the widget to the ring |
| Lock position | Ignores dragging |
| Interval | 30 s to 15 min, 2 min by default |
| Language | Automatic, Português, English |
| Start with Windows | Writes the entry under `HKCU\...\CurrentVersion\Run` |

Preferences live in `%APPDATA%\ClaudeUsageWidget\settings.json`.

### Language

The interface ships in English and Portuguese. It follows the Windows language by default; the
**Language** menu offers Automatic, Português and English, and the choice is saved. Switching
applies immediately, with no restart.

It is not only labels: the weekday (`Fri` / `sex`), the decimal mark (`6.0M` / `6,0M`) and the
plural of sessions follow the language too. Translating labels while the numbers stay in one locale
reads half converted, which is worse than not translating at all.

Strings live in `src/claude_usage/i18n.py`, one dictionary per language. Adding a language means
copying the English dictionary, translating the values and registering it in `LANGUAGES`; a test
keeps the keys and the `{format}` fields in step across every language.

## Layout

```
src/claude_usage/   application code    tests/       test suite
installer/          packaging           tools/       icon and preview generators
```

| Module | Role |
| --- | --- |
| `credentials.py` | Reads Claude Code's OAuth token |
| `api.py` | Usage and incidents; `parse()` split out so the contract tests without a network |
| `tokens.py` | Sums the window's tokens from local transcripts |
| `poller.py` | Collection thread, history, burn rate and projection |
| `theme.py` | Palette, 4pt spacing scale and formatters |
| `paint.py` | Drawing primitives: ring, meter, chip, shadow, icons |
| `brand.py` | The Claude Code mascot from the official SVG, embedded as a string |
| `i18n.py` | Interface strings, one dictionary per language |
| `widget.py` | The floating bar |
| `panel.py` | The expanded panel |
| `app.py` | Tray, menu and wiring |

## Development

```powershell
uv sync                                           # creates the .venv with the dev group
uv run pytest                                     # 81 tests, no network, no windows
uv run ruff check .                               # lint (rules in pyproject.toml)
uv run python tools/preview.py docs/preview.png   # offline render of both surfaces
$env:CLAUDE_USAGE_DEBUG=1; uv run claude-usage    # prints every cycle to the console
```

The render tests use `QT_QPA_PLATFORM=offscreen` (see `tests/conftest.py`) and check that every
painting path runs without raising, across the states the UI actually reaches: no data, live, error,
collecting and compact.

In that mode Qt swaps the Windows font database for a stub whose fallback runs about 1.8x wider than
Segoe UI. Two consequences:

- tests that measure text geometry are gated on the real font (the `real_fonts` fixture) and skip
  themselves when headless. To run the whole suite against the real thing:
  `$env:QT_QPA_PLATFORM = "windows"; uv run pytest`;
- `tools/preview.py` deliberately does **not** use offscreen: in that mode every glyph is a box.

## Building the installer

```powershell
.\installer\build.ps1                  # icon -> PyInstaller -> Inno Setup
.\installer\build.ps1 -SkipInstaller   # only the portable folder in build\dist
.\installer\build.ps1 -Clean           # wipes build\ first, caches included
```

Needs Inno Setup (`winget install JRSoftware.InnoSetup`); the script looks for both the per-user and
the machine-wide install. Output lands in `build\ClaudeUsage-Setup-<version>.exe`, about 21 MB
compressed from 70 MB installed. Every run leaves **exactly one** setup in the folder, the one just
built: keeping old versions side by side is how the wrong `.exe` gets shipped.

| File | Role |
| --- | --- |
| `installer/build.ps1` | Runs the three steps and reads the version from `pyproject.toml` |
| `installer/claude-usage.spec` | PyInstaller: onedir, no console, icon and version resource |
| `installer/claude-usage.iss` | Inno Setup: per-user install, shortcuts, autostart, uninstaller |
| `installer/entry.py` | Frozen entry point (`__main__.py` uses a relative import) |
| `tools/gen_icon.py` | Builds the multi-resolution `.ico` from the mascot SVG |

Three packaging decisions:

- **onedir, not onefile.** `--onefile` unpacks the whole Qt runtime into `%TEMP%` on every launch,
  a second or two for an app that lives in the tray and starts with Windows.
- **`opengl32sw.dll` left out.** That is 20 MB of Mesa's software OpenGL, a fifth of the bundle, and
  this interface is painted by Qt's raster engine alone.
- **The `.ico` is assembled by hand.** Importing Pillow into a PySide6 process loads a second
  libpng/zlib and Qt's PNG encoder dies with an access violation; writing the ICO container is 40
  lines and removes that whole class of DLL clash.

## Implementation notes

Things that cost time and that the code alone does not explain:

- **`QGraphicsDropShadowEffect` on a translucent window freezes the content** after the first frame
  on Windows; the widget painted `--` forever. The shadow is drawn by hand in `paint.shadow()` and
  each window reserves a transparent margin for it.
- **The receiver of the poller's signals must be a `QObject`.** Connected to a plain Python object
  the connection becomes direct, and painting happens on the collection thread.
- **Clicking the widget while the panel is open arrives in two parts.** The `Qt.Popup` closes itself
  on the outside click and the widget receives that same click next; without a guard the panel
  closed and reopened in one gesture. `Panel.just_closed()` swallows the second event for 250 ms.
- **Text is measured, never placed at a fixed offset.** `56min` is half again as wide as `2h13` and
  used to run into the clock column. Digits use `tnum` (`QFont.setFeature`), otherwise `1` is
  narrower than the other digits and the countdown jitters every second.

## Cost

Each cycle is a POST worth one output token. At two minutes, that is roughly 700 requests a day, all
of the smallest size possible. Raise the interval in the menu if it bothers you.

## License

MIT. See [LICENSE](LICENSE).
