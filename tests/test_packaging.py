"""Facts the build depends on that no other test would notice breaking.

The release workflow refuses a tag that disagrees with pyproject.toml, so a
version declared twice is the one thing that can turn a release red after three
builds have already run. Cheaper to catch here.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

import agent_gauge

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
VERSION = PYPROJECT["project"]["version"]


def test_the_package_agrees_with_pyproject():
    assert agent_gauge.__version__ == VERSION


def test_the_version_is_a_plain_triple():
    """The .exe resource wants four integer fields, built by padding this one."""
    assert re.fullmatch(r"\d+\.\d+\.\d+", VERSION), VERSION


def test_every_build_script_produces_the_same_name():
    """`AgentGauge-<version>`, one shape across three platforms. The .dmg is the
    exception on purpose: two Mac architectures ship in one release and would
    otherwise collide."""
    iss = (ROOT / "installer" / "agent-gauge.iss").read_text(encoding="utf-8")
    sh = (ROOT / "installer" / "build.sh").read_text(encoding="utf-8")

    assert "OutputBaseFilename=AgentGauge-{#MyAppVersion}" in iss
    assert 'out="build/AgentGauge-$version.AppImage"' in sh
    assert 'out="build/AgentGauge-$version-$arch.dmg"' in sh


def test_the_release_workflow_collects_those_names():
    release = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    for pattern in ("build/AgentGauge-*.exe", "build/AgentGauge-*.dmg",
                    "build/AgentGauge-*.AppImage"):
        assert pattern in release, pattern
