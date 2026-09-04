#!/usr/bin/env sh
# Start the widget detached from this terminal, the way run.bat does on Windows:
# closing the terminal afterwards leaves it running. Run `uv sync` once first.
cd "$(dirname "$0")" || exit 1
nohup .venv/bin/python -m claude_usage >/dev/null 2>&1 &
echo "claude-usage started (pid $!)"
