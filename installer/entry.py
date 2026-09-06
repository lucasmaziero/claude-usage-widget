"""Frozen-build entry point.

PyInstaller runs its entry script as a top-level module, so the package's own
`__main__.py` (which uses a relative import) cannot be used directly.
"""
from agent_gauge.app import main

raise SystemExit(main())
