@echo off
REM Start the widget without a console window. Run `uv sync` once first.
start "" "%~dp0.venv\Scripts\pythonw.exe" -m claude_usage
